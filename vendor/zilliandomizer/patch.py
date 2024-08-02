from collections import defaultdict
import os
from pathlib import Path
from typing import ClassVar, Dict, Generator, Iterable, List, Sequence, Set, Tuple, Union

from zilliandomizer.game import Game
from zilliandomizer.logic_components.items import KEYWORD, NORMAL, RESCUE
from zilliandomizer.logic_components.regions import RegionData
from zilliandomizer.low_resources import asm, ram_info, rom_info
from zilliandomizer.low_resources.item_rooms import item_room_codes
from zilliandomizer.options import ID, VBLR, Chars, char_to_jump, char_to_gun, chars
from zilliandomizer.utils import ItemData, parse_loc_name, parse_reg_name

ROM_NAME = "Zillion (UE) [!].sms"

paths: List[List[str]] = [
    ["."],  # important that this is first because empty string might be passed to Patcher for cwd
    ["roms"],
    ["src"],
    ["src", "roms"],
    ["src", "zilliandomizer"],
    ["src", "zilliandomizer", "roms"],
    [".."],
    ["..", "roms"],  # this one should find it according to the readme instructions
    ["..", ".."],
    ["..", "..", "roms"],
]
""" paths to search for rom """

# TODO: fix Champ rescue sprite in top rooms
# TODO: lots of JJ rescue graphic work


class ByteDict(Dict[int, int]):
    def __setitem__(self, key: int, value: int) -> None:
        assert 0 <= value <= 255, f"{value=}"
        return super().__setitem__(key, value)


class Patcher:
    writes: Dict[int, int]  # address to byte
    verify: bool

    end_of_available_banked: Dict[int, int]
    """ 0 for bank independent """

    demos_disabled: bool
    """ needed for bank 6 space """

    rom_path: str
    rom: bytes

    """ memory location of canister to Archipelago location id number """
    _init_code: bytearray

    BANK_OFFSETS: ClassVar[Dict[int, int]] = {
        0: 0,  # bank independent 0x0000 - 0x7fdf
        2: 0,  # bank 2 if I use (unbanked) 0x8000 through 0xbfff
        3: 0x4000,
        4: 0x8000,
        5: 0xc000,
        6: 0x10000,
        7: 0x14000,
    }

    def __init__(self, path_to_rom: Union[str, Path] = "") -> None:
        self.writes = {}  # debugging: ByteDict()
        self.verify = True
        self._init_code = bytearray()

        # 1st used byte after an unused section
        self.end_of_available_banked = {
            0: rom_info.free_space_end_7e00,
            # If we use the end of bank 4, it might collide with changed door data.
            # (If we don't change door data, there's space that could be used
            #  at the end of bank 4.)
            5: rom_info.bank_5_free_space_end_bfdf,
            6: rom_info.bank_6_free_space_end_b5e6,
        }
        self.demos_disabled = False

        if path_to_rom != "":
            path_to_rom = Path(path_to_rom)
            if str(path_to_rom).lower().endswith(".sms"):
                path_to_rom = path_to_rom.parent

        self.rom_path = str(path_to_rom)
        if self.rom_path == "":
            for path_list in paths:
                assert len(path_list)  # use "." for current directory
                path = os.sep.join(path_list)
                if os.path.exists(path + os.sep + ROM_NAME):
                    self.rom_path = path
                    break
        else:
            # rom path came from caller
            if not os.path.exists(os.path.join(self.rom_path, ROM_NAME)):
                self.rom_path = ""
        if self.rom_path == "":
            raise FileNotFoundError(f'unable to find original rom "{ROM_NAME}"')
        else:
            print(f"found rom at {self.rom_path}{os.sep}{ROM_NAME}")

            with open(f"{self.rom_path}{os.sep}{ROM_NAME}", "rb") as file:
                self.rom = file.read()
        assert Patcher.checksum(self.rom), "incorrect data in rom - invalid checksum"

    def fix_floppy_req(self) -> None:
        """
        The vanilla game requires an exact number of floppies to use the main computer.
        This patch changes it to require at least that number of floppies,
        instead of requiring the exact number.
        """
        # shortly after _LABEL_4FA5_ we compare the # of floppies with 5
        # I think that's saying "If we don't have a good number of floppies, jump to ++"
        # at 1899, we take the number of floppies, and subtract 6.
        # If that goes negative, then jump? I always get confused by subtract carry.
        # If we subtract x=5 and that DOES go negative, we don't have a good number of floppies. So jump?
        # jp c, ++
        # 01:4FB0 = 11011010 (DA) changed from 11000010 (C2)
        # 01:4FAF = number of floppies required
        addr = rom_info.floppy_req_instruction_4fb0
        if self.verify:
            assert self.rom[addr] == asm.JPNZ
        self.writes[addr] = asm.JPC

        # TODO: Investigate: I think there's another place in the code that checks the floppy requirement.
        # maybe something happens at the ship if you have them?

    def fix_floppy_display(self) -> None:
        """
        The vanilla game will display no more than 5 floppies on the pause screen.
        This fix changes it to 8, which is to the edge of the screen.
        This is only visual. You can pick up up to 255 floppies.
        """
        # rom addr 1899 set to 9
        # rom addr 189D set to 8
        # (if floppy_count >= 9: use 8 instead)
        # that will set max floppies displayed to 8
        # (if you go more than 8, they wrap around to the other side of the screen, we don't need that)
        # You can still get more floppies. It just won't show more than this setting.
        compare_addr = rom_info.floppy_display_compare_1899
        change_addr = rom_info.floppy_display_change_189d
        if self.verify:
            assert self.rom[compare_addr] == 0x06
            assert self.rom[change_addr] == 0x05
        self.writes[compare_addr] = 0x09
        self.writes[change_addr] = 0x08

    def fix_rescue_tile_load(self) -> None:
        """ load apple and champ rescue tiles when entering blue area and red area """
        bank_offset = Patcher.BANK_OFFSETS[7]  # I hope this bank is always loaded when this code runs
        # I don't _use_bank(7, code)
        # because this uses all of that space,
        # no room for anything else

        vram_load_lo = 0xae
        vram_load_hi = 0x03

        champ_lo = rom_info.champ_rescue_banked_tiles_8b93 % 256
        champ_hi = rom_info.champ_rescue_banked_tiles_8b93 // 256
        apple_lo = rom_info.apple_rescue_banked_tiles_8695 % 256
        apple_hi = rom_info.apple_rescue_banked_tiles_8695 // 256
        blue_lo = rom_info.blue_basic_banked_tiles_81fd % 256
        blue_hi = rom_info.blue_basic_banked_tiles_81fd // 256

        blue_code = [
            asm.LDHL, champ_lo, champ_hi,  # set of tiles that has champ's rescue
            asm.LDDE, 0xC0, 0x6F,  # where to put that data
            asm.CALL, vram_load_lo, vram_load_hi,
            asm.LDHL, apple_lo, apple_hi,  # set of tiles that has apple's rescue
            asm.LDDE, 0x20, 0x67,  # where to put that data
            asm.CALL, vram_load_lo, vram_load_hi,
            asm.LDHL, blue_lo, blue_hi,  # blue area canisters
            asm.RET
        ]
        # TODO: To fix the issue where this isn't loaded on unpause
        # (and death / continue), find where that 2nd to last line is
        # (asm.LDHL, blue_lo, blue_hi)
        # somewhere else in code when leaving pause screen or other scene.
        # Replace it with call to this.

        blue_code_addr = rom_info.bank_7_free_space_1ffdb
        banked_blue_addr = blue_code_addr - bank_offset

        for i in range(len(blue_code)):
            if self.verify:
                assert self.rom[blue_code_addr + i] == 0xff
            self.writes[blue_code_addr + i] = blue_code[i]

        red_code = [
            asm.LDHL, champ_lo, champ_hi,  # set of tiles that has champ's rescue
            asm.LDDE, 0xC0, 0x6F,  # where to put that data
            asm.CALL, vram_load_lo, vram_load_hi,
            asm.LDHL, apple_lo, apple_hi,  # set of tiles that has apple's rescue
            asm.RET
        ]

        red_code_addr = blue_code_addr + len(blue_code)
        banked_red_addr = red_code_addr - bank_offset

        for i in range(len(red_code)):
            if self.verify:
                assert self.rom[red_code_addr + i] == 0xff
            self.writes[red_code_addr + i] = red_code[i]

        blue_entry = rom_info.load_blue_code_10a3
        red_entry = rom_info.load_red_code_10cd

        if self.verify:
            assert self.rom[blue_entry + 0] == blue_code[-4]
            assert self.rom[blue_entry + 1] == blue_code[-3]
            assert self.rom[blue_entry + 2] == blue_code[-2]
            assert self.rom[red_entry + 0] == red_code[-4]
            assert self.rom[red_entry + 1] == red_code[-3]
            assert self.rom[red_entry + 2] == red_code[-2]
        self.writes[blue_entry + 0] = asm.CALL
        self.writes[blue_entry + 1] = banked_blue_addr % 256
        self.writes[blue_entry + 2] = banked_blue_addr // 256
        self.writes[red_entry + 0] = asm.CALL
        self.writes[red_entry + 1] = banked_red_addr % 256
        self.writes[red_entry + 2] = banked_red_addr // 256

    def fix_spoiling_demos(self) -> None:
        """
        The arcade-style demos that are played if no one presses start
        can spoil randomized information.

        This fix makes it so only the first demo plays.
        The first demo doesn't show any rooms, only hallways.
        """
        if self.verify:
            assert self.rom[rom_info.demo_inc] == asm.INCVHL
        self.writes[rom_info.demo_inc] = asm.NOP

        # this has the side-effect of freeing up lots of space in bank 6
        # (the data used to control the demos)
        self.demos_disabled = True

    def set_required_floppies(self, floppy_count: int) -> None:
        """ set how many floppies are required to use the main computer and win """
        # 01:4FAF = number of floppies required to use the main computer
        # 01:13EF = number of floppies required to win at the ship
        for addr in (rom_info.floppy_req_4faf, rom_info.floppy_req_13ef):
            if self.verify:
                assert self.rom[addr] == 0x05
            assert 0 <= floppy_count < 256
            self.writes[addr] = floppy_count

        # change introduction text to tell how many floppies are required
        addr = rom_info.floppy_intro_text_1a771
        original_text = b'THE 5 FLOPPY DISKS FROM'
        replacement = f"THE {floppy_count} FLOPPY DISKS FROM"
        if floppy_count > 9:
            replacement = f"{floppy_count} FLOPPY DISKS FROM  "
            if floppy_count < 100:
                replacement += " "
        replacement_bytes = replacement.encode("ascii")
        assert len(original_text) == len(replacement_bytes)
        for i in range(len(original_text)):
            if self.verify:
                assert self.rom[addr + i] == original_text[i]
            self.writes[addr + i] = replacement_bytes[i]

        # In vanilla, if you have exactly 4 floppies,
        # you can use "continue" after you die one extra time.
        # (Normally, you can only use "continue" 3 times,
        #  but if you have 4 floppies, you can use "continue" a 4th time.)
        # I'm not changing this. No matter how many floppies are required
        # to win, 4 is still the number of floppies that gives an extra
        # continue.

    def set_display_computer_codes_default(self, display: bool) -> None:
        """
        set the default cursor position to decide whether to show
        all the computer codes in the beginning text boxes

        original rom defaults to true
        """
        # selection is at ram C3A5 bit 4 - 0 (4C) for yes, 1 (5C) for no
        # but I had trouble finding what set the default
        # It gets set to 4C as soon as the option appears.
        # It's 00 since reset before that.
        # found it at 1d0c
        # The bit is also written to C707, but that's not the source of truth.

        address = rom_info.tutorial_menu_default_1d0c
        other_bits = 0x4c
        if self.verify:
            assert (self.rom[address] & 0b11101111) == other_bits
        write = other_bits | ((not display) << 4)
        # 0x1d09 should be [dd, 36, 05, 4c] by default
        self.writes[address] = write

    def set_start_char(self, char_order: Tuple[Chars, Chars, Chars]) -> None:
        """
        set which character you start the game with

        `char_order` is `start_char, captured_1, captured_2`
        """

        start_char, captured_1, captured_2 = char_order

        # c127 is current character: 0 jj, 1 champ, 2 apple
        # label AA9 sets c127 to 0 when "press start button" with ldir
        #         ld hl, _DATA_AFA_
        #         ld de, _RAM_C11E_
        #         ld bc, $000A
        #         ldir
        # so it looks like 0B03 gets copied to c127 to initialize it

        current_char_init_addr = rom_info.current_char_init_0b03
        if self.verify:
            assert self.rom[current_char_init_addr] == 0x00
        self.writes[current_char_init_addr] = {
            "JJ": 0x00,
            "Apple": 0x02,
            "Champ": 0x01
        }[start_char]

        # TODO: important!!! change the color of the tiny sprite that comes out of the ship

        # c150 is whether jj is "rescued"
        # c160 for Champ
        # c170 for Apple
        # whether they are rescued is initialized by _DATA_7B98_
        jj_rescue = rom_info.char_init_7b98
        champ_rescue = rom_info.char_init_7b98 + 16
        apple_rescue = rom_info.char_init_7b98 + 32
        # for whom to rescue
        apple_rescue_code = rom_info.apple_rescue_code_4bdb  # 70 change to 50 for jj
        champ_rescue_code = rom_info.champ_rescue_code_4be1  # 60 change to 50 for jj
        if self.verify:
            assert self.rom[jj_rescue] == 0x01
            assert self.rom[champ_rescue] == 0x00
            assert self.rom[apple_rescue] == 0x00
            assert self.rom[apple_rescue_code] == 0x70
            assert self.rom[champ_rescue_code] == 0x60
        self.writes[jj_rescue] = int(start_char == "JJ")
        self.writes[champ_rescue] = int(start_char == "Champ")
        self.writes[apple_rescue] = int(start_char == "Apple")
        if start_char == "Apple":
            # rescue JJ instead of Apple
            self.writes[apple_rescue_code] = 0x50
        elif start_char == "Champ":
            # rescue JJ instead of Champ
            self.writes[champ_rescue_code] = 0x50

        apple_text_addr = rom_info.apple_rescue_lines_1add8
        champ_text_addr = rom_info.champ_rescue_lines_1ae38

        # change text that char says depending on who is where
        apple_text: Dict[int, Tuple[bytes, bytes]] = {
            apple_text_addr[0]: (b'THANK YOU FOR', b'I<M SO GLAD  '),
            apple_text_addr[1]: (b'RESCUING ME:', b'THAT YOU<RE '),
            apple_text_addr[2]: (b'I<M SORRY THAT', b'ALL RIGHT>    '),
            apple_text_addr[3]: (b'I WAS CAPTURED:', b'JJ:            '),
            apple_text_addr[4]: (b'IS CHAMP', b'LET<S   '),
            apple_text_addr[5]: (b'ALL RIGHT;', b'GO:       ')
        }
        champ_text: Dict[int, Tuple[bytes, bytes]] = {
            champ_text_addr[0]: (b'YOU<RE', b'HOW DO'),
            champ_text_addr[1]: (b'VERY LATE:', b'WE KEEP   '),
            champ_text_addr[2]: (b'WHAT<VE YOU', b'GETTING IN '),
            champ_text_addr[3]: (b'BEEN DOING;', b'THIS MESS; '),
            champ_text_addr[4]: (b'AH> I<VE', b'LET<S   '),
            champ_text_addr[5]: (b'BUNGLED THINGS', b'GET OUT OF    '),
            champ_text_addr[6]: (b'BADLY:', b'HERE: ')
        }
        for old, new in apple_text.values():
            assert len(old) == len(new)
        for old, new in champ_text.values():
            assert len(old) == len(new)
        if self.verify:
            for addr in apple_text:
                old, _ = apple_text[addr]
                for i in range(len(old)):
                    # print(f"checking addr {hex(addr + i)}: {chr(self.rom[addr + i])} {chr(old[i])}")
                    assert self.rom[addr + i] == old[i]
            for addr in champ_text:
                old, _ = champ_text[addr]
                for i in range(len(old)):
                    assert self.rom[addr + i] == old[i]
        if start_char != "JJ":
            text = apple_text if start_char == "Apple" else champ_text
            for addr in text:
                _, new = text[addr]
                for i in range(len(new)):
                    self.writes[addr + i] = new[i]

        # starting text says who has been captured
        replace_text = f"{captured_1.upper()} AND {captured_2.upper()} ARE"
        need_space = len(rom_info.intro_rescue_text) - len(replace_text)
        replace_text += (" " * need_space)
        replace_text_bytes = replace_text.encode("ascii")
        for i in range(len(rom_info.intro_rescue_text)):
            addr = rom_info.intro_rescue_text_address + i
            if self.verify:
                assert self.rom[addr] == rom_info.intro_rescue_text[i]
            self.writes[addr] = replace_text_bytes[i]

    def set_item(self, address: int, data: ItemData) -> None:
        for i, v in enumerate(data):
            assert 0 <= v <= 255, f"item index {i} trying to write {v}"
            self.writes[address + i] = v

    @staticmethod
    def checksum(rom: Union[bytes, bytearray], update: bool = False) -> bool:
        """
        checks or updates (depending on `update`)

        (rom needs to be mutable for update)
        """
        total = sum(rom[:0x7ff0]) + sum(rom[0x8000:0x20000])
        checksum_lo = total & 0xff
        checksum_hi = (total >> 8) & 0xff
        if update:
            assert isinstance(rom, bytearray)
            rom[rom_info.checksum_7ffa] = checksum_lo
            rom[rom_info.checksum_7ffa + 1] = checksum_hi
            return True
        # else check
        return (rom[0x7ffa] == checksum_lo) and (rom[0x7ffb] == checksum_hi)

    def get_patched_bytes(self) -> bytearray:
        new_rom = bytearray(self.rom)  # copy
        self._finalize_init()
        for address in self.writes:
            new_rom[address] = self.writes[address]

        Patcher.checksum(new_rom, True)

        return new_rom

    def write(self, filename: str) -> None:
        if (filename != os.devnull) and (not filename.endswith(".sms")):
            filename += ".sms"
        new_rom = self.get_patched_bytes()

        if filename == os.devnull:
            full_path = filename
        else:
            full_path = f"{self.rom_path}{os.sep}{filename}"

        with open(full_path, "wb") as file:
            file.write(new_rom)

    def get_address_for_room(self, map_index: int) -> int:
        """ the address in the rom where this room's items are stored """
        index = rom_info.room_table_91c2 + 2 * map_index
        low = self.rom[index]
        high = self.rom[index + 1]
        return (high << 8) | low

    def get_item_rooms(self) -> Generator[int, None, None]:
        """
        addresses for the data structures of the items of each map index
        """
        for i in range(136):
            yield self.get_address_for_room(i)

    def item_count(self, rom_index: int) -> int:
        """ parameter is from `get_address_for_room` or `get_item_rooms` """
        return self.rom[rom_index]

    def get_items(self, rom_index: int) -> Generator[ItemData, None, None]:
        """ parameter is from `get_address_for_room` or `get_item_rooms` """
        start = rom_index + 1
        for _ in range(self.item_count(rom_index)):
            this_item = ItemData(*(self.rom[v] for v in range(start, start + 8)))
            yield this_item
            start += 8

    def write_locations(self,
                        regions: Iterable[RegionData],
                        start_char: Chars) -> None:
        items_placed_in_map_index: Dict[int, int] = defaultdict(int)
        for region in regions:
            for loc in region.locations:
                assert loc.item, "There should be an item placed in every location before " \
                                 f"writing locations. {loc.name} is missing item."
                if loc.item.code in {KEYWORD, NORMAL, RESCUE}:
                    row, col, y, x = parse_loc_name(loc.name)
                    map_index = row * 8 + col
                    rom_room = self.get_address_for_room(map_index)
                    item_no = items_placed_in_map_index[map_index]
                    try:
                        # different from map index and 2x item room index
                        room_code = next(self.get_items(rom_room)).room_code
                        assert room_code == item_room_codes[map_index], f"{room_code=} {item_room_codes[map_index]=}"
                    except StopIteration:
                        # This is to keep unit tests from failing with no rom data
                        print(f"ERROR: no item data for rom room {rom_room} at map index {map_index}")
                        room_code = 0

                    if loc.item.code == RESCUE:
                        y -= 8
                    r = room_code
                    m = 1 << item_no
                    i = loc.item.id
                    s = loc.req_gun * 2
                    # different sprite for red and paperclip
                    if map_index >= 80:
                        s += 12
                    elif map_index >= 40:
                        s += 6
                    if loc.item.code == RESCUE:
                        if start_char == "Apple":
                            s = 0x16  # use Champ rescue sprite for both JJ and Champ
                        else:
                            s = loc.item.id * 2 + 0x14
                    g = max(0, loc.req_gun - 1)
                    new_item_data = ItemData(loc.item.code, y, x, r, m, i, s, g)
                    self.set_item(rom_room + 1 + 8 * item_no, new_item_data)
                    items_placed_in_map_index[map_index] += 1
            if region.computer != b'\xff':
                row, col = parse_reg_name(region.name)
                map_index = row * 8 + col
                rom_room = self.get_address_for_room(map_index)
                computer_address = rom_room + 1 + 8 * self.item_count(rom_room)
                self.writes[computer_address] = region.computer[0]
                self.writes[computer_address + 1] = region.computer[1]

    def _use_bank(self, bank_no: int, code: Sequence[int]) -> int:
        """
        put `code` into rom in bank `bank_no`

        returns banked address of new code

        bank 0 is limited, only use it if really needed
        """
        if bank_no == 6:
            assert self.demos_disabled, "using this memory bank requires `fix_spoiling_demos`"
        assert bank_no in Patcher.BANK_OFFSETS, f"invalid bank number {bank_no}"
        assert bank_no in self.end_of_available_banked, f"no known free space in bank {bank_no}"

        code_len = len(code)

        new_code_addr_banked = self.end_of_available_banked[bank_no] - code_len
        self.end_of_available_banked[bank_no] = new_code_addr_banked
        new_code_addr = new_code_addr_banked + Patcher.BANK_OFFSETS[bank_no]

        if bank_no == 6:
            # in bank 6, we're replacing demo control data,
            # so instead of verifying it, just make sure it's doesn't overflow
            assert new_code_addr_banked > rom_info.bank_6_second_demo_control_b14a, "overflow bank 6"

        # print(f"programming {code_len} bytes for new bank {bank_no} code at {hex(new_code_addr)}")
        for i in range(code_len):
            write_addr = new_code_addr + i
            if self.verify and (bank_no != 6):
                assert self.rom[write_addr] == 0xff, "overflow"
            self.writes[write_addr] = code[i]
        return new_code_addr_banked

    def _run_at_init(self, code: Iterable[int]) -> None:
        """
        set code to run when start button is pressed on title screen, to initialize game

        bank 5
        """
        self._init_code.extend(code)

    def _finalize_init(self) -> None:
        if (
            rom_info.init_splice_address_0ac3 + 1 in self.writes or
            rom_info.init_splice_address_0ac3 + 2 in self.writes
        ):
            print("WARNING: Either someone spliced into init manually, "
                  "or they're getting the patched bytes more than once.")
            return

        self._init_code.extend([
            asm.JP, rom_info.init_splice_target_2e7d & 0xff, rom_info.init_splice_target_2e7d // 256
        ])

        # bank 5 is loaded at init (I hope)
        init_address = self._use_bank(5, self._init_code)

        if self.verify:
            assert self.rom[rom_info.init_splice_address_0ac3 + 1] == rom_info.init_splice_target_2e7d & 0xff
            assert self.rom[rom_info.init_splice_address_0ac3 + 2] == rom_info.init_splice_target_2e7d // 256
        self.writes[rom_info.init_splice_address_0ac3 + 1] = init_address & 0xff
        self.writes[rom_info.init_splice_address_0ac3 + 2] = init_address // 256

    def set_new_opa_level_system(self, opas_per_level: int, hp_per_level: int = 20, max_level: int = 8) -> None:
        """
        Letting the player choose who to level up has a few drawbacks:
         - possible softlock from making bad choices (nobody has jump 3 when it's required)
         - In multiworld, you won't be able to choose because you won't know it's coming beforehand.

        So with this new system:
         - Everyone levels up together (even if they're not rescued yet).
         - You can choose how many opa-opas are required for a level up.
         - You can set a max level from 1 to 8.
         - The currently active character is still the only one that gets the health refill.
           - TODO: Change this to choose based on missing (effective) health, and/or an option to refill everyone.
        """
        rom_hp_per_level = round(hp_per_level / 10)
        if not (hp_per_level % 10 == 0):
            print(f"warning: hp_per_level needs to be multiple of 10, rounding to {rom_hp_per_level * 10}")
        max_level = min(8, max_level)  # limited to 3 bits, would be difficult to change
        max_level = max(1, max_level)

        # original code location
        old_hi = rom_info.level_up_code_4adf // 256
        old_lo = rom_info.level_up_code_4adf % 256

        # this is the location of the "+" label of the 4ADF section of code in the rom
        _4ADF_plus_hi = rom_info.level_up_code_plus_4aeb // 256
        _4ADF_plus_lo = rom_info.level_up_code_plus_4aeb % 256

        # ram locations for each char's level
        lv_hi = 0xc1
        lv_jj_lo = 0x55
        lv_ch_lo = 0x65
        lv_ap_lo = 0x75

        # subroutine that does the work of leveling up
        # separated because we don't want it taking space in bank independent memory
        # hl pointing at jj's level before calling
        lots_of_work_to_do = bytearray([
            # level up all chars
            asm.INCVHL,
            asm.LDHL, lv_ch_lo, lv_hi,
            asm.INCVHL,
            asm.LDHL, lv_ap_lo, lv_hi,
            asm.INCVHL,

            # load jumps into pause screen data so we can see them
            asm.LDAVHL,  # (Apple's) level into a
            asm.ADDAA,
            asm.ADDAA,  # multiply by 4
            asm.LDCA,  # put it in c
            asm.LDBI, 0x00,
            asm.LDHL, 0xc9, 0x7c,  # jj level 0 jump
            asm.ADDHLBC,  # jj current level jump
            asm.LDAVHL,
            asm.LDVA, 0x58, 0xc1,
            asm.LDCI, 0x20,  # difference between each character
            asm.ADDHLBC,  # move to Champ's data
            asm.LDAVHL,
            asm.LDVA, 0x68, 0xc1,
            asm.ADDHLBC,  # move to Apple's data
            asm.LDAVHL,
            asm.LDVA, 0x78, 0xc1,

            # change hp and max hp by hp per level
            asm.LDAV, 0x51, 0xc1,  # JJ max hp
            asm.ADDAI, rom_hp_per_level,
            asm.DAA,
            asm.LDVA, 0x51, 0xc1,
            asm.LDAV, 0x53, 0xc1,  # JJ curr hp
            asm.ADDAI, rom_hp_per_level,
            asm.DAA,
            asm.LDVA, 0x53, 0xc1,
            asm.LDAV, 0x61, 0xc1,  # Champ max hp
            asm.ADDAI, rom_hp_per_level,
            asm.DAA,
            asm.LDVA, 0x61, 0xc1,
            asm.LDAV, 0x63, 0xc1,  # Champ curr hp
            asm.ADDAI, rom_hp_per_level,
            asm.DAA,
            asm.LDVA, 0x63, 0xc1,
            asm.LDAV, 0x71, 0xc1,  # Apple max hp
            asm.ADDAI, rom_hp_per_level,
            asm.DAA,
            asm.LDVA, 0x71, 0xc1,
            asm.LDAV, 0x73, 0xc1,  # Apple curr hp
            asm.ADDAI, rom_hp_per_level,
            asm.DAA,
            asm.LDVA, 0x73, 0xc1,
            asm.RET
        ])

        work_addr_banked = self._use_bank(6, lots_of_work_to_do)

        # new ram going to use - hope it's not already used
        opa_hi = ram_info.opas_c2ee >> 8
        opa_lo = ram_info.opas_c2ee & 0xff

        new_code = bytearray([
            # get opa opa
            asm.LDAV, opa_lo, opa_hi,
            asm.INCA,
            asm.CP, opas_per_level,
            asm.JRZ, 6,
            asm.LDVA, opa_lo, opa_hi,
            asm.JP, _4ADF_plus_lo, _4ADF_plus_hi,

            # check if max level
            asm.XORA,
            asm.LDVA, opa_lo, opa_hi,
            asm.LDHL, lv_jj_lo, lv_hi,
            asm.LDAVHL,
            asm.CP, max_level - 1,  # memory values are 0 to 7
            asm.JPNC, _4ADF_plus_lo, _4ADF_plus_hi,

            # subroutine in bank 6 for lots of work
            asm.LDAV, 0xff, 0xff,
            asm.PUSHAF,
            asm.LDAI, 0x06,
            asm.LDVA, 0xff, 0xff,
            asm.CALL, work_addr_banked & 0xff, work_addr_banked >> 8,
            asm.POPAF,
            asm.LDVA, 0xff, 0xff,

            asm.JP, old_lo, old_hi
        ])
        # this has to use bank independent memory because
        # it jumps to different places that depend on the bank
        new_code_addr = self._use_bank(0, new_code)

        # change jump table to point at new code
        # table at 4ABC, 2 bytes for each entry, we want entry 9 for opa-opa
        entry = rom_info.item_pickup_jump_table_4abc + 2 * ID.opa
        if self.verify:
            assert self.rom[entry] == old_lo
            assert self.rom[entry + 1] == old_hi
        self.writes[entry] = new_code_addr % 256
        self.writes[entry + 1] = new_code_addr // 256

    def set_scope_distribute(self) -> None:
        """
        if current character already has scope, give scope to Apple, Champ, JJ

        It might go to the current character twice,
        if the character status database isn't updated.
        (Shouldn't be a big problem: default has 4 scopes, can avoid by pausing after you get scope.)
        """

        new_get_scope_code = bytearray([
            asm.LDHL, ram_info.curr_scope_c149 & 0xff, ram_info.curr_scope_c149 // 256,
            asm.LDAVHL,
            asm.ORA,
            asm.JRZ, 20,  # jump to increment
            # check apple
            asm.LDHL, ram_info.apple_scope_c179 & 0xff, ram_info.apple_scope_c179 // 256,
            asm.LDAVHL,
            asm.ORA,
            asm.JRZ, 13,  # jump to increment
            # check champ
            asm.LDHL, ram_info.champ_scope_c169 & 0xff, ram_info.champ_scope_c169 // 256,
            asm.LDAVHL,
            asm.ORA,
            asm.JRZ, 6,  # jump to increment
            # check jj
            asm.LDHL, ram_info.jj_scope_c159 & 0xff, ram_info.jj_scope_c159 // 256,
            asm.LDAVHL,
            asm.ORA,
            asm.RETNZ,
            # increment this one
            asm.INCVHL,
            # make alarms visible in current room (copied from original increment scope code)
            # only necessary for c149 (should already be set for the others),
            # but it doesn't hurt to do it with all
            asm.LDHL, ram_info.alarm_status_c26a & 0xff, ram_info.alarm_status_c26a // 256,
            asm.SET_B_HL_LO, asm.SET_7_HL_HI,
            asm.RET
        ])
        using_bank = 6
        get_scope_addr = self._use_bank(using_bank, new_get_scope_code)

        # original increment scope code
        inc_scope_lo = rom_info.increment_scope_code_4b07 & 0xff
        inc_scope_hi = rom_info.increment_scope_code_4b07 // 256

        # We just need the beginning of the (save bank, set new bank, call, restore bank) pattern.
        # The rest will replace the original increment scope code.
        save_bank_code = bytearray([
            asm.LDAV, 0xff, 0xff,
            asm.PUSHAF,
            asm.JP, inc_scope_lo, inc_scope_hi,
        ])

        bank_switch_to_scope = self._use_bank(0, save_bank_code)

        # change jump table to point at new code
        # table at 4ABC, 2 bytes for each entry, we want entry for scope
        entry = rom_info.item_pickup_jump_table_4abc + 2 * ID.scope
        if self.verify:
            assert self.rom[entry] == inc_scope_lo
            assert self.rom[entry + 1] == inc_scope_hi
        self.writes[entry] = bank_switch_to_scope & 0xff
        self.writes[entry + 1] = bank_switch_to_scope // 256

        replacing_increment_scope = bytearray([
            asm.LDAI, using_bank,
            asm.LDVA, 0xff, 0xff,
            asm.CALL, get_scope_addr & 0xff, get_scope_addr // 256,
            asm.POPAF,
            asm.LDVA, 0xff, 0xff,
            asm.RET  # this 1 byte already there
        ])

        original_inc_scope_code = new_get_scope_code[:5] + bytearray([asm.RETNZ]) + new_get_scope_code[-7:]
        # print(list(original_inc_scope_code))

        assert len(replacing_increment_scope) == len(original_inc_scope_code), "scope code doesn't fit right"

        for i in range(len(replacing_increment_scope)):
            address = rom_info.increment_scope_code_4b07 + i
            if self.verify:
                assert self.rom[address] == original_inc_scope_code[i]
            self.writes[address] = replacing_increment_scope[i]

    def set_jump_levels(self, jump_option: VBLR) -> None:
        # because of r13c1y98x10, this function also sets speed to 1 higher than jump
        # speed is the byte after jump in stats_per_level_table_7cc8
        # speed is the byte before jump in char_init_7b98

        # vanilla speed values for verification
        speed_values: Dict[Chars, List[int]] = {
            "JJ": [1, 1, 1, 1, 2, 2, 3, 3],
            "Champ": [0, 0, 0, 0, 1, 1, 2, 2],
            "Apple": [2, 2, 2, 2, 3, 3, 3, 3]
        }

        table_addr = rom_info.stats_per_level_table_7cc8
        jump_base = table_addr + 1

        init_table_jump = rom_info.char_init_7b98 + 8  # jump in initialization of char data

        for char_i, char in enumerate(chars):
            jump_addr = init_table_jump + char_i * 16
            speed_addr = jump_addr - 1
            if self.verify:
                # print(char)
                # print(self.rom[jump_addr], char_to_jump[char]["vanilla"][0] - 1)
                assert self.rom[jump_addr] == char_to_jump[char]["vanilla"][0] - 1
                assert self.rom[speed_addr] == speed_values[char][0]
            self.writes[jump_addr] = char_to_jump[char][jump_option][0] - 1
            self.writes[jump_addr - 1] = self.writes[jump_addr] + 1

            for level_i in range(8):
                addr = jump_base + char_i * 32 + level_i * 4
                if self.verify:
                    assert self.rom[addr] == char_to_jump[char]["vanilla"][level_i] - 1
                    assert self.rom[addr + 1] == speed_values[char][level_i]
                self.writes[addr] = char_to_jump[char][jump_option][level_i] - 1
                self.writes[addr + 1] = self.writes[addr] + 1  # speed

    def set_new_gun_system_and_levels(self, gun: VBLR) -> None:
        MAX_GUN_LEVEL_COUNT = 7
        table = bytearray(len(chars) * MAX_GUN_LEVEL_COUNT)
        for char_i, char in enumerate(chars):
            gun_levels = char_to_gun[char][gun][:]
            while len(gun_levels) < MAX_GUN_LEVEL_COUNT:
                gun_levels.append(gun_levels[-1])
            for level_i in range(MAX_GUN_LEVEL_COUNT):
                table[level_i * len(chars) + char_i] = gun_levels[level_i] - 1
        # 21 byte table
        # I haven't looked at moving gun code out of bank independent yet.
        # It probably can be moved if I need more space.
        table_addr = self._use_bank(0, table)

        # initialization of gun data
        init_table_gun = rom_info.char_init_7b98 + 6  # gun in initialization of char data
        for table_i, addr in enumerate(range(init_table_gun, init_table_gun + 33, 16)):
            if self.verify:
                assert self.rom[addr] == char_to_gun[chars[table_i]]["vanilla"][0] - 1
            self.writes[addr] = table[table_i]

        # new ram going to use - hope it's not already used
        new_gun_hi = ram_info.guns_c2ec >> 8
        new_gun_lo = ram_info.guns_c2ec & 0xff

        # ram locations for each char's gun level
        gn_hi = 0xc1
        gn_cu_lo = 0x46
        gn_jj_lo = 0x56
        gn_ch_lo = 0x66
        gn_ap_lo = 0x76

        # the vanilla code to go back to after incrementing guns
        after_gun_hi = rom_info.code_after_increment_gun_7c1e // 256
        after_gun_lo = rom_info.code_after_increment_gun_7c1e % 256

        new_gun_code = bytearray([
            asm.LDAV, new_gun_lo, new_gun_hi,
            asm.LDCA,
            asm.ADDAA,
            asm.ADDAC,
            asm.LDCA,  # c = 3 * gun
            asm.LDBI, 0x00,
            asm.LDHL, table_addr % 256, table_addr // 256,
            asm.ADDHLBC,
            asm.LDAVHL,  # JJ's gun level
            asm.LDVA, gn_jj_lo, gn_hi,
            asm.INCHL,
            asm.LDAVHL,  # Champ's gun level
            asm.LDVA, gn_ch_lo, gn_hi,
            asm.INCHL,
            asm.LDAVHL,  # Apple's gun level
            asm.LDVA, gn_ap_lo, gn_hi,
            # now the current char gun level
            asm.LDAV, 0x27, 0xc1,  # current char
            asm.ADDAA,
            asm.ADDAA,
            asm.ADDAA,
            asm.ADDAA,
            asm.LDCA,  # c = 16 * current char
            asm.LDBI, 0x00,
            asm.LDHL, gn_jj_lo, gn_hi,
            asm.ADDHLBC,
            asm.LDAVHL,
            asm.LDVA, gn_cu_lo, gn_hi,
            asm.JP, after_gun_lo, after_gun_hi
        ])
        # length 48
        new_code_addr = self._use_bank(0, new_gun_code)
        # TODO: This looks like it can be moved to a different bank.
        # just a jump at the end - It can RET to somewhere in bank 0
        # that resets bank and does that jump.

        gun_inc = rom_info.increment_gun_code_4af8

        # now change existing increment gun code to point at that new code
        changes: Dict[int, Tuple[int, int]] = {
            gun_inc + 0: (gn_cu_lo, new_gun_lo),  # increment at this address
            gun_inc + 1: (gn_hi, new_gun_hi),
            gun_inc + 4: (0x02, MAX_GUN_LEVEL_COUNT - 1),  # compare value for limit
            gun_inc + 8: (after_gun_lo, new_code_addr % 256),  # jump here if we incremented
            gun_inc + 9: (after_gun_hi, new_code_addr // 256)
        }
        for addr in changes:
            old, new = changes[addr]
            if self.verify:
                assert self.rom[addr] == old
            self.writes[addr] = new

    def set_continues(self, count: int) -> None:
        """
        set how many continues you can use before a game over

        -1 is infinity (never game over)
        """
        # TODO: change text that says "THE CONTINUE FEATURE CAN BE USED ONLY THREE TIMES"
        if count == -1:
            # infinity
            # it's important for this code that continue_count_init
            # doesn't get changed from it's vanilla 4 value
            code = [
                asm.BIT_B_HL_LO, asm.BIT_2_HL_HI,  # test bit 2 in (hl) (see if (hl) is 4)
                asm.JRZ, 0x100 - 13,               # jr z, -13
            ]
            for i in range(len(code)):
                addr = rom_info.continue_dec_addr_2523 + i
                if self.verify:
                    assert self.rom[addr] == rom_info.continue_dec_code[i]
                self.writes[addr] = code[i]
        else:  # not infinity
            if self.verify:
                assert self.rom[rom_info.continue_count_init_0af5] == 4
            self.writes[rom_info.continue_count_init_0af5] = count + 1

    def set_new_game_over(self, continue_count: int) -> None:
        """
        game over is no fun

        change to teleport back to ship on game over
         - keep items
         - cancel base explosion command
         - reset continues

        This feature requires `fix_spoiling_demos` (for memory space).
        """
        # TODO: FIXME: If I get a game over while elevator moving,
        # (likely in base explosion)
        # I get stuck with the vertical movement,
        # and crash the game when I go too high
        # ram c1a8 ?  c311 ?
        # c316 to 01 - partial fix, puts in frozen state ( that happens when I get hit while looking in canister )
        # TODO: FIXME: If I get a game over in a gradually scrolling area
        # (hallway), it can bug an elevator and/or the ship
        # and make the game impossible.
        # (Can reset if using zri memory.)
        assert self.writes[rom_info.demo_inc] == asm.NOP, "set_new_game_over requires fix_spoiling_demos"

        bank_of_new_code = 0x06

        teleport_code = bytearray([
            asm.LDAV, 0xff, 0xff,  # bank number
            asm.PUSHAF,
            asm.LDAI, 0x04,
            asm.LDVA, 0xff, 0xff,
            asm.LDAI, 0x00,
            asm.LDVA, 0x29, 0xc3,  # map row
            asm.LDAI, 0x03,
            asm.JP, 0xeb, 0x1f,  # vanilla teleport code (used for both warp 6 and warp 7)
        ])

        # jumps to code that depends on bank
        teleport_addr = self._use_bank(0, teleport_code)

        new_game_over_code = bytearray([
            asm.CALL, teleport_addr & 0xff, teleport_addr >> 8,
            # position initialized by c1ad flag
            # asm.LDAI, 0x50,
            # asm.LDVA, 0x05, 0xc3,  # y position
            # asm.LDAI, 0x18,
            # asm.LDVA, 0x03, 0xc3,  # x position
            asm.XORA,
            # if this flag is turned off,
            # it will think the beginning scene hasn't been initialized and initialize it
            asm.LDVA, 0xad, 0xc1,
            asm.CALL, 0x97, 0x20,  # cancel explosion command
            asm.LDAI, continue_count + 1,
            asm.LDVA, 0x12, 0xc1,  # numbers of continues in ram

            # unlock char movement, in case it was locked when base exploded
            asm.LDAI, 0x01,
            asm.LDVA, 0x16, 0xc3,

            asm.XORA,
            asm.LDVA, 0x86, 0xc1,  # set not in room transition
            asm.LDVA, 0x87, 0xc1,  # stop moving walkway animation
            asm.LDVA, 0x8a, 0xc1,  # stop barriers (for sound effect)

            asm.CALL, 0xcc, 0x24,  # continue code that sets hp
            # asm.LDAI, 0x07,  # ship scene
            # asm.CALL, 0xd3, 0x24,  # continue code that sets hp
            asm.RET,
        ])

        new_game_over_address_banked = self._use_bank(bank_of_new_code, new_game_over_code)

        # wrapper for bank changing
        game_over_wrapper = bytearray([
            asm.LDAI, bank_of_new_code,
            asm.LDVA, 0xff, 0xff,
            asm.CALL, new_game_over_address_banked & 0xff, new_game_over_address_banked >> 8,
            asm.RET,
        ])

        # length 9
        new_code_addr = self._use_bank(0, game_over_wrapper)

        # now call that new code when game over happens
        new_code = [asm.JP, new_code_addr & 0xff, new_code_addr >> 8]
        for i in range(len(new_code)):
            a = rom_info.game_over_code_retry_24c2 + i
            b = rom_info.game_over_code_0_continues_251a + i
            if self.verify:
                assert self.rom[a] == rom_info.game_over_code[i]
                assert self.rom[b] == rom_info.game_over_code[i]
            self.writes[a] = new_code[i]
            self.writes[b] = new_code[i]

        explode_jump_lo = 0x89
        explode_jump_hi = 0x06

        # in base explosion, change number of continues to 0
        explode_game_over_code = bytearray([
            asm.XORA,  # 0 into a
            asm.LDVA, 0x12, 0xc1,  # continues
            asm.LDAI, 0xa3,  # code that was going to be executed in vanilla
            asm.JP, explode_jump_lo, explode_jump_hi,
        ])

        # too short to be worth a wrapper to different bank
        explode_addr = self._use_bank(0, explode_game_over_code)

        # change jump location to that code
        if self.verify:
            assert self.rom[rom_info.base_explosion_jump_2112] == explode_jump_lo
            assert self.rom[rom_info.base_explosion_jump_2112 + 1] == explode_jump_hi
        self.writes[rom_info.base_explosion_jump_2112] = explode_addr & 0xff
        self.writes[rom_info.base_explosion_jump_2112 + 1] = explode_addr >> 8

        # go to scene with continues instead of scene without continues
        if self.verify:
            assert self.rom[rom_info.base_explosion_scene_210b] == 0x06
        self.writes[rom_info.base_explosion_scene_210b] = 0x07

    def fix_white_knights(self) -> None:
        original = b'=ZILLION= MEN'
        better = b'WHITE KNIGHTS'
        assert len(original) == len(better)
        for i in range(len(original)):
            for t_i in rom_info.zillion_men_1ae99_1af22:
                addr = t_i + i
                if self.verify:
                    assert self.rom[addr] == original[i]
                self.writes[addr] = better[i]

    def set_external_item_interface(self, start_char: Chars, max_level: int) -> None:
        """
        If another program can read and write the ram of this game,
        (RetroArch READ_CORE_RAM and WRITE_CORE_RAM)
        it can give items to the player.

        ram address c2ex
        where x is:
         - an item id 5 or higher
         - 3 to rescue apple (or jj if apple is the starting character)
         - 4 to rescue champ (or jj if champ is the starting character)
        put the total count of each item given to the game

        Example:
            To bring the total number of scopes given
            through this interface to 2, put a 2 in c2eb,
            because 0x0b is the item id for scope.

        This value should only ever be increased, never decreased.
        (You can't take back an item after it's given.)
        """
        # 3 into this interface is the apple rescue scene
        # 4 into this interface is the champ rescue scene
        # (These are normally keyword 4 and empty, which won't be sent.)
        rescue = {
            3: 0x70,
            4: 0x60,
        }
        if start_char == "Apple":
            rescue[3] = 0x50
        elif start_char == "Champ":
            rescue[4] = 0x50

        # before getting to this code,
        # a is which item we're picking up,
        # hl points to how many of this item we picked up
        pickup_code = bytearray([
            asm.RETC,  # I've picked up more than I've been given?

            asm.INCVHL,  # picked up one more of this item

            # check if item or rescue
            asm.CP, 0x04,
            asm.JRZ, 15,  # champ
            asm.JRC, 18,  # apple

            # item
            # TODO: instead of canister sound, make a new cutscene for scene 6
            # for telling which item and who it came from
            # (based on cutscene 0 because that's a short cutscene that goes back to gameplay)
            # Maybe that should be optional because of the extra time it takes.
            asm.PUSHAF,  # push item id to stack
            asm.LDAI, 0x97,  # get canister sound
            asm.LDVA, 0x05, 0xc0,  # sound trigger ram
            asm.POPAF,  # pop item id from stack
            # could save space, but use extra clock cycles to jump to where these next 2 lines are
            asm.LDHL, 0xbc, 0x4a,
            asm.JP, 0x20, 0x00,  # This jump leads to something with with `ret` instruction.

            # champ
            asm.LDHL, rescue[4], 0xc1,
            asm.JR, 0x03,  # after_apple
            # apple
            asm.LDHL, rescue[3], 0xc1,
            # after_apple
            asm.SET_B_HL_LO, asm.SET_0_HL_HI,

            asm.LDVA, 0x83, 0xc1,  # scene selector

            # set music
            asm.LDAI, 0x84,  # rescue music
            # asm.LDVA, 0x05, 0xc0,  # sound trigger - This didn't work well.
            # It didn't go back to normal music after the cutscene.
            asm.CALL, 0x89, 0x06,

            asm.LDAI, 0x06,  # cutscene
            asm.LDVA, 0x1e, 0xc1,  # scene trigger

            # done processing item
            asm.RET,

            # copied from 4a1a, don't understand what this does
            # something to do with facing the canister and/or showing text box
            # 0xfd, 0x36, 0x16, 0x13,  # ld (iy+22), $13
            # 0xfd, 0xcb, 0x08, 0xde,  # set 3, (iy+8)
            # 0xfd, 0xcb, 0x08, 0xee,  # set 5, (iy+8)
            # set 3, (ix+8)  # this is for the local room, so not here
        ])
        pickup_addr = self._use_bank(6, pickup_code)

        item_ram_hi = ram_info.item_pickup_queue // 256
        item_ram_pushed_lo = ram_info.item_pickup_queue & 0xff
        item_ram_picked_lo = ram_info.item_pickup_record & 0xff

        check_interface_code = bytearray([
            asm.LDAV, ram_info.current_scene_c11f % 256, ram_info.current_scene_c11f // 256,
            asm.CP, 0x8b,
            asm.RETNZ,  # return if not in scene b (gameplay scene)

            asm.LDAV, ram_info.in_room_transition_c186 % 256, ram_info.in_room_transition_c186 // 256,
            asm.ORA,
            asm.RETNZ,  # return if in room transition

            asm.LDHI, item_ram_hi,
        ])
        for item_id in range(0x03, 0x0c):
            each_item = bytearray([
                asm.LDAV, item_ram_pushed_lo + item_id, item_ram_hi,
                asm.LDLI, item_ram_picked_lo + item_id,
                asm.CPVHL,
                asm.LDAI, item_id,
                asm.JPNZ, pickup_addr % 256, pickup_addr // 256
            ])
            check_interface_code.extend(each_item)
        check_interface_code.append(asm.RET)

        check_address_banked = self._use_bank(6, check_interface_code)

        # I might want to move this after some of the other checks in this area.
        # I'm not sure what all of them do.
        # It's important that this points to a 3 byte instruction.
        # TODO: move to rom_info after well tested
        common_gameplay_0x0c71 = 0x0c71
        splice = common_gameplay_0x0c71

        # don't know if I need to save current bank
        bank_wrapper = bytearray([
            asm.LDAI, 0x06,
            asm.LDVA, 0xff, 0xff,
            asm.CALL, check_address_banked & 0xff, check_address_banked >> 8,
            self.rom[splice], self.rom[splice + 1], self.rom[splice + 2],  # code replaced by jump here
            asm.JP, (splice + 3) & 0xff, (splice + 3) >> 8,
        ])

        # length 14
        new_code_addr = self._use_bank(0, bank_wrapper)

        if self.verify:
            assert self.rom[splice] == bank_wrapper[-6]
            assert self.rom[splice + 1] == bank_wrapper[-5]
            assert self.rom[splice + 2] == bank_wrapper[-4]
        self.writes[splice] = asm.JP
        self.writes[splice + 1] = new_code_addr & 0xff
        self.writes[splice + 2] = new_code_addr >> 8

    def old_set_external_item_interface(self, start_char: Chars, max_level: int) -> None:
        """
        deprecated
        keeping around for now, for comparison

        If another program can read and write the ram of this game,
        (RetroArch READ_CORE_RAM and WRITE_CORE_RAM)
        it can give items to the player.

        ram address c2ea
         - put an item id 5 or higher to give the player that item
         - put a 3 there to rescue apple (or jj if apple is the starting character)
         - put a 4 there to rescue champ (or jj if champ is the starting character)

        The game will set that address to 0 when it has finished processing that item.
        """
        # new ram going to use - hope it's not already used
        item_flag_hi = ram_info.deprecated_external_item_trigger_c2ea // 256
        item_flag_lo = ram_info.deprecated_external_item_trigger_c2ea % 256

        # 3 into this interface is the apple rescue scene
        # 4 into this interface is the champ rescue scene
        # (These are normally keyword 4 and empty, which won't be sent.)
        rescue = {
            3: 0x70,
            4: 0x60,
        }
        if start_char == "Apple":
            rescue[3] = 0x50
        elif start_char == "Champ":
            rescue[4] = 0x50

        check_interface_code = bytearray([
            asm.LDAV, 0x1f, 0xc1,  # current scene
            asm.CP, 0x8b,
            asm.RETNZ,  # return if not in scene b (gameplay scene)

            # I need to be able to communicate to the external interface
            # whether I'm at the max level.
            # Every frame, I write the max level (-1) to ram.
            # (I thought about putting it in opa get code,
            #  to not run every frame, but that uses limited bank 0 space.)
            asm.LDAI, max_level - 1,
            asm.LDVA, ram_info.max_level & 0xff, ram_info.max_level >> 8,

            asm.LDHL, item_flag_lo, item_flag_hi,
            asm.LDAVHL,
            asm.ORA,
            asm.RETZ,  # no external item

            # check if item or rescue
            asm.CP, 0x04,
            asm.JRZ, 14,  # champ
            asm.JRC, 19,  # apple

            # item
            # TODO: instead of canister sound, make a new cutscene for scene 6
            # for telling which item and who it came from
            # (based on cutscene 0 because that's a short cutscene that goes back to gameplay)
            # Maybe that should be optional because of the extra time it takes.
            asm.LDAI, 0x97,  # get canister sound
            asm.LDVA, 0x05, 0xc0,  # sound trigger ram
            asm.LDAVHL,  # item id to get
            asm.LDVHLI, 0x00,  # done processing this item
            # could save space, but use extra clock cycles to jump to where these next 2 lines are
            asm.LDHL, 0xbc, 0x4a,
            asm.JP, 0x20, 0x00,  # This jump leads to something with with `ret` instruction.

            # champ
            asm.LDHL, rescue[4], 0xc1,
            asm.JR, 0x03,  # after_apple
            # apple
            asm.LDHL, rescue[3], 0xc1,
            # after_apple
            asm.SET_B_HL_LO, asm.SET_0_HL_HI,

            asm.LDVA, 0x83, 0xc1,  # scene selector

            # set music
            # if c005 doesn't work well, can try this:
            # ld a, $84
            # call _SET_MUSIC_LABEL_689_
            asm.LDAI, 0x84,  # rescue music
            asm.LDVA, 0x05, 0xc0,  # sound trigger

            asm.LDAI, 0x06,  # cutscene
            asm.LDVA, 0x1e, 0xc1,  # scene trigger

            # done processing item
            asm.XORA,
            asm.LDVA, item_flag_lo, item_flag_hi,
            asm.RET,

            # copied from 4a1a, don't understand what this does
            # something to do with facing the canister and/or showing text box
            # 0xfd, 0x36, 0x16, 0x13,  # ld (iy+22), $13
            # 0xfd, 0xcb, 0x08, 0xde,  # set 3, (iy+8)
            # 0xfd, 0xcb, 0x08, 0xee,  # set 5, (iy+8)
            # set 3, (ix+8)  # this is for the local room, so not here
        ])

        check_address_banked = self._use_bank(6, check_interface_code)

        # I might want to move this after some of the other checks in this area.
        # I'm not sure what all of them do.
        # It's important that this points to a 3 byte instruction.
        # TODO: move to rom_info after well tested
        common_gameplay_0x0c71 = 0x0c71
        splice = common_gameplay_0x0c71

        # don't know if I need to save current bank
        bank_wrapper = bytearray([
            asm.LDAI, 0x06,
            asm.LDVA, 0xff, 0xff,
            asm.CALL, check_address_banked & 0xff, check_address_banked >> 8,
            self.rom[splice], self.rom[splice + 1], self.rom[splice + 2],  # code replaced by jump here
            asm.JP, (splice + 3) & 0xff, (splice + 3) >> 8,
        ])

        # length 14
        new_code_addr = self._use_bank(0, bank_wrapper)

        if self.verify:
            assert self.rom[splice] == bank_wrapper[-6]
            assert self.rom[splice + 1] == bank_wrapper[-5]
            assert self.rom[splice + 2] == bank_wrapper[-4]
        self.writes[splice] = asm.JP
        self.writes[splice + 1] = new_code_addr & 0xff
        self.writes[splice + 2] = new_code_addr >> 8

    def set_multiworld_items(self, loc_to_names: Dict[str, Tuple[str, str]]) -> None:
        """
        set the text to display for specific canisters

        (These canisters should have the "EMPTY" item.)

        loc_to_names is { location_name: (item_name, text_to_display)}
        """

        # everything here happens with bank 5 already loaded (I hope)
        bank = 5

        # to match "EMPTY" in rom
        name_length = 5

        def clean_name_for_rom(player_name: str) -> str:
            cleaned = ""
            for char in player_name:
                char = char.upper()
                if 'A' <= char <= 'Z':
                    cleaned += char
                # TODO: get available digits
                if len(cleaned) >= name_length:
                    break
            while len(cleaned) < name_length:
                cleaned += ' '
            return cleaned

        name_to_clean_name: Dict[str, str] = {}
        clean_names: Set[str] = set()

        for _, player_name in loc_to_names.values():
            # In tests, I was able to put 93 names in the rom without overflow.
            # But let's leave some margin for things to change.
            if len(clean_names) > 70:
                cleaned = "AP   "
            else:
                cleaned = clean_name_for_rom(player_name)
            assert len(cleaned) == name_length

            name_to_clean_name[player_name] = cleaned
            clean_names.add(cleaned)

        # make table of names:
        # 0x05 - 5 letters - 0x05 - 5 letters - 0x05 - 5 letters - ...
        # so the table looks the same as entries from 77d2 - 11 bytes for each name
        name_tile_table = bytearray()

        # enumeration of player names
        clean_name_to_tile_index: Dict[str, int] = {}

        for i, cleaned in enumerate(sorted(clean_names)):
            clean_name_to_tile_index[cleaned] = i

            name_tile_table.append(name_length)
            for char in cleaned:
                address = rom_info.font_tiles[char]
                banked = address - Patcher.BANK_OFFSETS[bank]
                assert 0x8000 <= banked <= 0xbfff
                lo = banked & 0xff
                hi = banked >> 8
                name_tile_table.append(lo)
                name_tile_table.append(hi)

        banked_name_tile_table_addr = self._use_bank(bank, name_tile_table)

        # make a table like 75fe - 2 bytes for each name
        # address pointing to entry in name_tile_table
        name_table = bytearray(2 * len(clean_name_to_tile_index))

        tile_entry_length = 1 + 2 * name_length
        for table_index in clean_name_to_tile_index.values():
            tile_addr = banked_name_tile_table_addr + table_index * tile_entry_length
            name_table[table_index * 2] = tile_addr & 0xff
            name_table[table_index * 2 + 1] = tile_addr >> 8

        banked_name_table_addr = self._use_bank(bank, name_table)

        # except instead of moving a register to point to entries in this table,
        # we move the base hl pointer so that an index 0x04 points where we want
        # so calculate what hl needs to be for each name to be at index 4

        # the address of 4 entries behind the entry
        entry_to_hl: Dict[int, int] = {
            i: banked_name_table_addr + (i - 4) * 2
            for i in range(len(clean_name_to_tile_index))
        }

        # identify a canister with 2 bytes: room and coord (y hi nybble and x hi nybble)
        # pack multi items:
        # group_count - room coord l h - room coord l h - ... - group_count - ...
        # group based on hi nybble of room

        location_groups: Dict[int, bytearray] = defaultdict(bytearray)

        for location_name in loc_to_names:
            _, player_name = loc_to_names[location_name]
            row, col, y, x = parse_loc_name(location_name)
            room = row * 8 + col
            coord = (y & 0xf0) | (x >> 4)

            group_id = room >> 4

            hl = entry_to_hl[clean_name_to_tile_index[name_to_clean_name[player_name]]]
            hl_lo = hl & 0xff
            hl_hi = hl >> 8

            location_groups[group_id].append(room)
            location_groups[group_id].append(coord)
            location_groups[group_id].append(hl_lo)
            location_groups[group_id].append(hl_hi)

        # save location of each group_count
        group_id_to_offset: Dict[int, int] = {}

        canister_list = bytearray()

        for group_id in range(9):
            group = location_groups[group_id]
            group_count = len(group) // 4

            group_id_to_offset[group_id] = len(canister_list)

            canister_list.append(group_count)
            canister_list.extend(group)

        banked_canister_list_addr = self._use_bank(bank, canister_list)

        group_id_to_addr = {
            group_id: banked_canister_list_addr + offset
            for group_id, offset in group_id_to_offset.items()
        }

        group_addr_table = bytearray(2 * 9)

        for group_id in range(9):
            addr = group_id_to_addr[group_id]
            addr_lo = addr & 0xff
            addr_hi = addr >> 8

            group_addr_table[group_id * 2] = addr_lo
            group_addr_table[group_id * 2 + 1] = addr_hi

        banked_group_addr_table_addr = self._use_bank(bank, group_addr_table)
        gat_lo = banked_group_addr_table_addr & 0xff
        gat_hi = banked_group_addr_table_addr >> 8

        map_index_ram_lo = 0x98
        map_index_ram_hi = 0xc1
        y_coord_ram_lo = 0x05
        x_coord_ram_lo = 0x03
        coord_ram_hi = 0xc3

        code = bytearray([
            asm.LDHL, 0xfe, 0x75,  # instruction that was replaced with jump to here
            asm.CP, 0x04,  # not empty canister?
            asm.JPNZ, 0xee, 0x73,  # back where we came from

            asm.LDAV, map_index_ram_lo, map_index_ram_hi,
            asm.SRL_LO, asm.SRL_A_HI,  # shift right
            asm.SRL_LO, asm.SRL_A_HI,  # shift right
            asm.SRL_LO, asm.SRL_A_HI,  # shift right
            asm.SRL_LO, asm.SRL_A_HI,  # shift right
            asm.LDHL, gat_lo, gat_hi,
            asm.RST10,  # now hl is in group of canister list
            # are there any multi items in this group
            asm.LDAVHL,
            asm.ORA,
            asm.JRZ, 46,  # end_of_group,  # nothing in this group
            asm.LDBA,
            # next_canister:
            asm.INCHL,  # map index
            asm.LDAV, map_index_ram_lo, map_index_ram_hi,
            asm.SUBVHL,
            asm.JRZ, 3,  # room_match,
            # room didn't match
            asm.INCHL,  # coord
            asm.JR, 31,  # no_match,
            # room_match:
            # check coord
            asm.LDAV, y_coord_ram_lo, coord_ram_hi,
            asm.ANDN, 0xf0,
            asm.LDCA,
            asm.LDAV, x_coord_ram_lo, coord_ram_hi,
            asm.ADDAI, 0x07,  # this is the rounding the game does to match player x with canister
            asm.SRL_LO, asm.SRL_A_HI,  # shift right
            asm.SRL_LO, asm.SRL_A_HI,  # shift right
            asm.SRL_LO, asm.SRL_A_HI,  # shift right
            asm.SRL_LO, asm.SRL_A_HI,  # shift right
            asm.ORC,
            asm.INCHL,  # coord
            asm.SUBVHL,
            asm.JRNZ, 7,  # no_match,  # 24 bytes since room_match
            # match:
            asm.INCHL,  # new hl lo
            asm.LDAVHL,
            asm.INCHL,  # new hl hi
            asm.LDHVHL,
            asm.LDLA,
            asm.JR, 7,  # done,  # 7 bytes since match
            # no_match:
            asm.INCHL,  # l
            asm.INCHL,  # h
            asm.DJNZ, 0xd3,  # -45 next_canister,
            # end_of_group:
            asm.LDHL, 0xfe, 0x75,  # original tile table for "EMPTY"
            # done:
            asm.LDAI, 0x04,  # still needs to think this is empty canister
            asm.JP, 0xee, 0x73,  # back where we came from
        ])

        banked_code_addr = self._use_bank(bank, code)
        code_lo = banked_code_addr & 0xff
        code_hi = banked_code_addr >> 8

        if self.verify:
            assert self.rom[0x73eb] == asm.LDHL
            assert self.rom[0x73ec] == 0xfe
            assert self.rom[0x73ed] == 0x75
        self.writes[0x73eb] = asm.JP
        self.writes[0x73ec] = code_lo
        self.writes[0x73ed] = code_hi

    def set_rom_to_ram_data(self, data: bytes) -> None:
        """
        put some specific data in ram, so it can be read externally

        truncated to 95 bytes
        """
        if len(data) > 95:
            data = data[:95]
        data = data + b'\x00'

        # at the splice point we use, we're already in bank 5
        using_bank = 5

        data_location = self._use_bank(using_bank, data)

        destination_lo = ram_info.rom_to_ram_data & 0xff
        destination_hi = ram_info.rom_to_ram_data // 256

        startup_splice_address = rom_info.startup_splice_26e5

        startup_splice_jump_lo = self.rom[startup_splice_address]
        startup_splice_jump_hi = self.rom[startup_splice_address + 1]

        code = bytearray([
            asm.LDHL, data_location & 0xff, data_location // 256,
            asm.LDDE, destination_lo, destination_hi,
            asm.LDBC, len(data), 0x00,
            asm.LDIR_LO, asm.LDIR_HI,
            asm.JP, startup_splice_jump_lo, startup_splice_jump_hi,
        ])

        code_address = self._use_bank(using_bank, code)

        self.writes[startup_splice_address] = code_address & 0xff
        self.writes[startup_splice_address + 1] = code_address // 256

        # game init clears out that ram, so need to write it again
        code = code[:-3]
        self._run_at_init(code)

    def set_defense(self, skill: int) -> None:
        """ change the defense (damage taken) of the characters according to skill level """
        # damage taken
        vanilla: Dict[Chars, List[int]] = {
            "JJ": [3, 3, 3, 3, 2, 2, 2, 1],
            "Champ": [2, 2, 2, 2, 1, 1, 1, 1],
            "Apple": [4, 4, 4, 4, 2, 2, 2, 1]
        }
        balanced: List[List[int]] = [
            [2, 2, 2, 1, 1, 1, 1, 1],
            [2, 2, 2, 2, 1, 1, 1, 1],
            [2, 2, 2, 2, 2, 1, 1, 1],
            [3, 2, 2, 2, 2, 1, 1, 1],
            [3, 3, 2, 2, 2, 1, 1, 1],
            [3, 3, 3, 2, 2, 1, 1, 1],
            [3, 3, 3, 2, 2, 2, 1, 1],
            [3, 3, 3, 2, 2, 2, 2, 1],
            [4, 3, 3, 3, 2, 2, 2, 1],
            [4, 4, 3, 3, 2, 2, 2, 1],
            [4, 4, 4, 3, 3, 2, 2, 1],
            [4, 4, 4, 4, 3, 3, 2, 1],
        ]
        difficulty_mods: Dict[Chars, int] = {
            "JJ": 4,
            "Champ": 0,
            "Apple": 6
        }
        # length of `balanced` needs to be (highest skill level + Apple difficulty_mod + 1)
        assert len(balanced) == 5 + difficulty_mods["Apple"] + 1

        for level in range(8):
            for char_i, char in enumerate(chars):
                difficulty_mod = difficulty_mods[char]
                address = rom_info.stats_per_level_table_7cc8 + char_i * 32 + level * 4 + 3
                if self.verify:
                    assert self.rom[address] == vanilla[char][level]
                self.writes[address] = balanced[skill + difficulty_mod][level]

    def set_explode_timer(self, time: int) -> None:
        """ set the amount of time to escape """
        if self.verify:
            assert self.rom[rom_info.base_explosion_timer_init_207b] == 0x00
            assert self.rom[rom_info.base_explosion_timer_init_207b + 1] == 0x03
            assert self.rom[rom_info.base_explosion_timer_text_6044] == ord("3")
            assert self.rom[rom_info.base_explosion_timer_text_6044 + 1] == ord("0")
            assert self.rom[rom_info.base_explosion_timer_text_6044 + 2] == ord("0")
        # bcd
        hundreds = time // 100
        tens = (time % 100) // 10
        ones = time % 10
        lo = (tens << 4) | ones
        # print("time", time, hex(hundreds), hex(lo))
        self.writes[rom_info.base_explosion_timer_init_207b] = lo
        self.writes[rom_info.base_explosion_timer_init_207b + 1] = hundreds
        self.writes[rom_info.base_explosion_timer_text_6044] = ord("0") + hundreds
        self.writes[rom_info.base_explosion_timer_text_6044 + 1] = ord("0") + tens
        self.writes[rom_info.base_explosion_timer_text_6044 + 2] = ord("0") + ones

    def set_starting_cards(self, starting_cards: int) -> None:
        """
        start the game with `starting_cards` cards
        and, on ship refill, receive `starting_cards` cards
        if you have less than that

        0 gives vanilla behavior (refill still gives 1 card)
        """
        if starting_cards == 0:
            return  # vanilla behavior

        card_floor = bytearray([
            asm.LDHL, ram_info.card_count_c129 & 0xff, ram_info.card_count_c129 // 256,
            asm.LDAVHL,
            asm.CP, starting_cards,
            asm.JRNC, 2,
            asm.LDVHLI, starting_cards,
            asm.RET
        ])
        card_floor_address = self._use_bank(0, card_floor)

        card_init = bytearray([
            asm.CALL, card_floor_address & 0xff, card_floor_address // 256,
        ])
        self._run_at_init(card_init)

        # also call card floor at ship refill
        refill_replacement = bytearray([
            asm.CALL, card_floor_address & 0xff, card_floor_address // 256,
            # I was going to fill with NOP to the end of the 8 bytes,
            # but the code that's there won't do anything anyway.
            # (HL is still pointing at the card count.)
        ])
        if self.verify:
            assert self.rom[rom_info.refill_card_injection_address_1389] == asm.LDHL
            assert self.rom[rom_info.refill_card_injection_address_1389 + 1] == ram_info.card_count_c129 & 0xff
            assert self.rom[rom_info.refill_card_injection_address_1389 + 2] == ram_info.card_count_c129 // 256
        self.writes[rom_info.refill_card_injection_address_1389] = refill_replacement[0]
        self.writes[rom_info.refill_card_injection_address_1389 + 1] = refill_replacement[1]
        self.writes[rom_info.refill_card_injection_address_1389 + 2] = refill_replacement[2]

        # not changing the number of cards from a continue (3)

    def set_infinite_hallway_bread(self) -> None:
        """ by resetting the room, you can pick up hallway bread an infinite number of times """
        if self.verify:
            assert self.rom[rom_info.save_hallway_bread_4714] == asm.LDVHLA
        self.writes[rom_info.save_hallway_bread_4714] = asm.NOP

    def all_fixes_and_options(self, game: Game) -> None:
        options = game.options
        self.writes.update(game.resource_writes)
        self.fix_floppy_display()
        self.fix_floppy_req()
        self.fix_rescue_tile_load()
        self.fix_spoiling_demos()
        self.fix_white_knights()
        self.set_display_computer_codes_default(options.tutorial)
        self.set_start_char(game.char_order)
        self.set_required_floppies(options.floppy_req)
        self.set_new_opa_level_system(options.opas_per_level, 20, options.max_level)
        self.set_new_gun_system_and_levels(options.gun_levels)
        self.set_jump_levels(options.jump_levels)
        self.set_continues(options.continues)
        self.set_new_game_over(options.continues)
        if (options.balance_defense):
            self.set_defense(options.skill)
        self.set_explode_timer(game.escape_time)
        self.set_starting_cards(options.starting_cards)
        self.set_scope_distribute()
        self.set_infinite_hallway_bread()
