import asyncio
from collections import Counter
from dataclasses import dataclass
import sys
from types import TracebackType
from typing import Dict, Iterable, Optional, Sequence, Tuple, Iterator
import typing

from zilliandomizer.logic_components.items import RESCUE, NORMAL
from zilliandomizer.low_resources import ram_info, rom_info
from zilliandomizer.options import Chars
from zilliandomizer.zri.events import DeathEventFromGame, DoorEventFromGame, \
    DoorEventToGame, EventFromGame, EventToGame, AcquireLocationEventFromGame, \
    ItemEventToGame, DeathEventToGame, MapEventFromGame, WinEventFromGame
from zilliandomizer.zri.rai import RAInterface, DOOR_BYTE_COUNT, RamDataWrapper
from zilliandomizer.zri.ram_interface import RamInterface

BYTE_ORDER = sys.byteorder
# mypy doesn't see literal types of byteorder

ITEM_BYTE_COUNT = 0x0c
""" highest item id is 0x0b, using from 0 to 0x0b """


@dataclass
class RescueInfo:
    start_char: Chars
    room_code: int
    """ 0-146 even numbers, double the item_room_index """
    mask: int


def bits(n: int) -> Iterator[int]:
    """ yield each activated bit of n """
    while n:
        b = n & ((~n) + 1)
        yield b
        n ^= b


def bytes_or(a: bytes, b: bytes) -> bytes:
    assert len(a) == len(b), f"requires parameters the same length, {len(a)}, {len(b)}"
    return bytes(a[i] | b[i] for i in range(len(a)))


class State:
    doors: bytes
    """ opened """
    received_items: bytearray
    """ index is item id (rescues 3 and 4) """

    def __init__(self, ram: Optional[RamDataWrapper] = None) -> None:
        if ram:
            self.doors = ram[ram_info.door_state_d600: ram_info.door_state_d600 + DOOR_BYTE_COUNT]
            self.received_items = bytearray(
                ram[ram_info.item_pickup_queue: ram_info.item_pickup_queue + ITEM_BYTE_COUNT]
            )
        else:
            self.reset()

    def reset(self) -> None:
        self.doors = bytes(0 for _ in range(DOOR_BYTE_COUNT))
        self.received_items = bytearray(0 for _ in range(ITEM_BYTE_COUNT))

    def anything_lost(self, old: "State") -> bool:
        _, door_lost, _ = get_changed_lost(self.doors, old.doors)
        # items_lost = any(self.received_items[i] < old.received_items[i]
        #                  for i in range(ITEM_BYTE_COUNT))

        # self.diff_cache = StateDiffCache(door_change, door_lost, door_int)

        return bool(door_lost)  # or bool(items_lost)


c11f_in_game_scenes = frozenset((
    # continue, explode, cs, ship, computer, pause, play, main computer
    3, 4, 6, 7, 8, 9, 0xb, 0xc
))


def get_changed_lost(new: Iterable[int], old: Iterable[int]) -> Tuple[int, int, int]:
    """
    changed bits, lost bits, new bits as `int`
    """
    new_int = int.from_bytes(new, BYTE_ORDER)
    old_int = int.from_bytes(old, BYTE_ORDER)
    changed = new_int ^ old_int
    lost = changed & old_int
    return changed, lost, new_int


class Memory:
    """
    puts in from_game_queue when sees events in game

    consumes to_game_queue
    """

    _rai: RamInterface
    rescues: Dict[int, Tuple[int, int]] = {}
    """ { ram_char_status_address: (item_room_index, mask) } """
    loc_mem_to_loc_id: Dict[int, int]
    """ { ((item_room_index << 8) | bit_mask): location_id } """
    from_game_queue: "Optional[asyncio.Queue[EventFromGame]]"
    to_game_queue: "asyncio.Queue[EventToGame]"

    _restore_target: Optional[State]

    known_doors: bytes
    known_cans: Iterable[int]
    known_in_game: bool
    known_win_state: bool
    known_dead: bool
    known_map: bool

    state: State

    def __init__(self,
                 from_game_queue: "Optional[asyncio.Queue[EventFromGame]]" = None,
                 to_game_queue: "Optional[asyncio.Queue[EventToGame]]" = None) -> None:
        """
        `rescues` maps a rescue id (0 or 1) to a canister location where that rescue is

        `loc_mem_to_loc_id` maps memory location of canister (room code and bit mask) to location id
        """
        self._rai = RAInterface()

        self.from_game_queue = from_game_queue
        self.to_game_queue = to_game_queue or asyncio.Queue()

        self.state = State()
        self.reset_game_state()

    async def read(self) -> RamDataWrapper:
        return RamDataWrapper(await self._rai.read())

    def get_rom_to_ram_data(self, ram: RamDataWrapper) -> bytes:
        """
        given the ram from `read()`,
        returns the data passed to zilliandomizer.patch.Patcher.set_rom_to_ram_data,
        padded with null (0x00) at end,
        empty (len 0) bytes if not available
        """
        if not ram.all_present():
            return b''

        return ram[ram_info.rom_to_ram_data: ram_info.rom_to_ram_data + 96]

    def set_generation_info(self,
                            rescues: Dict[int, RescueInfo],
                            loc_mem_to_loc_id: Dict[int, int]) -> None:
        self.rescues = {}
        for rescue_id, ri in rescues.items():
            if ri.start_char == "JJ":
                address = ram_info.apple_status_c170 if rescue_id == 0 else ram_info.champ_status_c160
            elif ri.start_char == "Apple":
                address = ram_info.jj_status_c150 if rescue_id == 0 else ram_info.champ_status_c160
            else:  # start char Champ
                address = ram_info.apple_status_c170 if rescue_id == 0 else ram_info.jj_status_c150
            self.rescues[address] = (ri.room_code // 2, ri.mask)

        self.loc_mem_to_loc_id = loc_mem_to_loc_id

    def have_generation_info(self) -> bool:
        return len(self.loc_mem_to_loc_id) > 0

    def reset_game_state(self) -> None:
        self.rescues = {}
        self.loc_mem_to_loc_id = {}

        self._restore_target = None

        self.known_in_game = False
        self.known_win_state = False
        self.known_dead = False
        self.known_map = False
        self.known_doors = bytes(0 for _ in range(DOOR_BYTE_COUNT))
        self.known_cans = bytes(0 for _ in range(rom_info.CANISTER_ROOM_COUNT))

        self.state.reset()

    def __enter__(self) -> "Memory":
        return self

    def close(self) -> None:
        self._rai.close()

    def __exit__(self, type: type, value: Exception, traceback: TracebackType) -> None:
        self.close()

    def _in_game(self, scene: int) -> bool:
        """ given the scene value from ram, process and return whether the game is started """
        in_game = (scene & 0x7f) in c11f_in_game_scenes
        if in_game != self.known_in_game:
            print(f"in game: {in_game}")
            self.known_in_game = in_game
        return in_game

    def _died(self, scene: int, cutscene: int, hp: int) -> bool:
        """
        given the scene (c11f), cutscene (c183), and hp (c143)
        return whether the player just died
        """
        # checking a few different parts of the death sequence,
        # just in case we miss the 0 hp in gameplay scene
        scene = scene & 0x7f
        dead = hp == 0 and (scene in {0x0b, 0x09} or (
            scene == 0x06 and cutscene in {2, 7}  # snnff and he he he
        ))
        event = False
        if dead and (dead != self.known_dead):
            print("death")
            event = True
        self.known_dead = dead
        return event

    def _looked_at_map(self, scene: int, computer_state: Sequence[int]) -> bool:
        """
        given the scene (c11f) and the computer state (c280 - c28b)
        return whether the player just used the map code
        """
        scene = scene & 0x7f
        looking_at_map = (
            scene == 8 and
            computer_state[0] == 1 and computer_state[1] == 1 and computer_state[2] == 1 and computer_state[3] == 1 and
            computer_state[7] == 0x0c and computer_state[11] == 1
        )
        event = False
        if looking_at_map and (looking_at_map != self.known_map):
            print("looked at map")
            event = True
        self.known_map = looking_at_map
        return event

    def _process_change(self, new_cans: Iterable[int]) -> None:
        """
        Take the canister pickups from memory and find out what's new.

        Put the acquire event in queue if a new canister has been picked up.
        """
        # report
        change, _, new_int = get_changed_lost(new_cans, self.known_cans)
        added = change & new_int
        added_rooms = added.to_bytes(rom_info.CANISTER_ROOM_COUNT, BYTE_ORDER)

        # indexes into `added_rooms`
        added_room_indexes = [i for i, b in enumerate(added_rooms) if b]

        for item_room_index in added_room_indexes:
            for can in bits(added_rooms[item_room_index]):
                print(f"picked up canister {can} in room {item_room_index}")
                if self.from_game_queue is None:
                    continue
                loc_memory = (item_room_index << 8) | (can)
                if loc_memory not in self.loc_mem_to_loc_id:
                    continue
                loc_id = self.loc_mem_to_loc_id[loc_memory]
                self.from_game_queue.put_nowait(
                    AcquireLocationEventFromGame(loc_id)
                )

    async def _process_to_game_queue(self, ram: RamDataWrapper, q: "asyncio.Queue[EventToGame]") -> None:
        if q.qsize():
            if ram.safe_to_write():
                event = q.get_nowait()
                if isinstance(event, ItemEventToGame):
                    counts = Counter(event.ids)
                    await self._process_items(counts)
                elif isinstance(event, DeathEventToGame):
                    await self._rai.write(0xc308, [0x84])
                elif isinstance(event, DoorEventToGame):
                    if len(event.doors) == len(self.state.doors):
                        self.state.doors = bytes_or(self.state.doors, event.doors)
                    else:
                        print(f"WARNING: invalid DoorEventToGame, length: {len(event.doors)}")
                else:
                    print(f"WARNING: unhandled EventToGame {event}")
                q.task_done()
            # else not a good time to send something to game
        # else queue empty

    async def _process_items(self, counts: typing.Counter[int]) -> None:
        counts_to_ram = bytearray(0 for _ in range(ITEM_BYTE_COUNT))
        for comm_item_id in counts:
            code = comm_item_id >> 8
            item_id = comm_item_id & 0xff
            if item_id == 0x04:  # empty
                # don't send empties to game
                continue
            if code == RESCUE:
                if item_id in (0, 1):
                    # 3 Apple, 4 Champ
                    item_id += 3
                else:
                    print(f"WARNING: invalid item id {comm_item_id} received with code rescue")
            elif code == NORMAL:
                if 0x05 <= item_id <= 0x0b:
                    pass
                else:
                    print(f"WARNING: invalid item id {comm_item_id} received with code normal")
            else:  # not rescue or normal
                print(f"WARNING: invalid item code {code} received")
            counts_to_ram[item_id] = counts[comm_item_id]
        if all((counts_to_ram[i] >= self.state.received_items[i])
               for i in range(ITEM_BYTE_COUNT)):
            for i in range(ITEM_BYTE_COUNT):
                new_count = counts_to_ram[i] - self.state.received_items[i]
                if new_count:
                    print(f"sending item {i}: {new_count}")
            await self._rai.write(ram_info.item_pickup_queue, counts_to_ram)
            self.state.received_items = counts_to_ram
        else:
            print(f"WARNING: sync problem - items lost {counts_to_ram} < {self.state.received_items}")

    async def process_ram(self, ram: RamDataWrapper) -> None:
        """ put info from game (that came from `read()`) into `from_game` queue """
        if not ram.all_present():
            return

        current_scene = ram[ram_info.current_scene_c11f]
        if self._in_game(current_scene):
            if self._restore_target:
                await self._restore(ram)
            else:
                self._check_win(ram)

                hp = ram[ram_info.current_hp_c143]  # BCD
                cutscene = ram[ram_info.cutscene_selector_c183]
                if self._died(current_scene, cutscene, hp) and not (self.from_game_queue is None):
                    self.from_game_queue.put_nowait(DeathEventFromGame())

                map_index = ram[ram_info.map_current_index_c198]
                if self._looked_at_map(
                    current_scene, ram[ram_info.computer_state_c280:ram_info.computer_state_c280 + 12]
                ) and not (self.from_game_queue is None):
                    self.from_game_queue.put_nowait(MapEventFromGame(map_index))

                current_state = State(ram)

                lost = current_state.anything_lost(self.state)

                if lost and map_index < 8:  # outside of base
                    self._restore_target = self.state
                else:
                    self.state.doors = bytes_or(current_state.doors, self.state.doors)
                    if self.known_doors != current_state.doors:
                        self.known_doors = current_state.doors
                        if self.from_game_queue:
                            self.from_game_queue.put_nowait(DoorEventFromGame(self.state.doors))

                    canisters = bytearray(ram[
                        ram_info.canister_state_d700 + 1:
                        ram_info.canister_state_d700 + rom_info.CANISTER_ROOM_COUNT * 2:
                        2
                    ])
                    assert len(canisters) == rom_info.CANISTER_ROOM_COUNT

                    # rescues don't show up in canister state,
                    # so we set the canister bits here according to the character status
                    for address, canister in self.rescues.items():
                        item_room_index, mask = canister
                        if ram[address] > 0:
                            canisters[item_room_index] |= mask
                        else:  # not rescued
                            canisters[item_room_index] &= (~mask)

                    self._process_change(canisters)
                    self.known_cans = canisters

                    pushed_items = ram[
                        ram_info.item_pickup_queue:
                        ram_info.item_pickup_queue + ITEM_BYTE_COUNT
                    ]
                    self.state.received_items = bytearray(pushed_items)

                    await self._process_to_game_queue(ram, self.to_game_queue)
        # else not in game

    async def _restore(self, ram: RamDataWrapper) -> None:
        if self._restore_target is None:
            return
        if ram.safe_to_write():
            print("doing restore")
            print("target:")
            print(self._restore_target)

            current = State(ram)
            print("current:")
            print(current)

            # TODO: get doors stored on AP server

            to_write = bytes_or(current.doors, self._restore_target.doors)

            if current.doors == to_write:
                self._restore_target = None
                print("restore finished")
                return

            # restore doors
            await self._rai.write(ram_info.door_state_d600, to_write)

    def _check_win(self, ram: RamDataWrapper) -> None:
        """
        check for win state in game and
        if a new win state is found, put win event in from queue
        """
        current_win_state = ram.in_win()
        if current_win_state and not self.known_win_state:
            print("found win")
            self.known_win_state = current_win_state
            if not (self.from_game_queue is None):
                self.from_game_queue.put_nowait(
                    AcquireLocationEventFromGame(0)
                )
                self.from_game_queue.put_nowait(
                    WinEventFromGame()
                )
