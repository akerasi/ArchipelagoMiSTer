from random import gauss, random, randrange, sample, shuffle
from typing import Dict, FrozenSet, Iterable, List, Literal, Mapping, Optional, Sequence, Set, Tuple, Union

from zilliandomizer.alarm_data import ALARM_ROOMS
from zilliandomizer.logic_components.location_data import make_locations
from zilliandomizer.logic_components.locations import Location, Req
from zilliandomizer.low_resources.room_data import map_index_to_loc_count
from zilliandomizer.low_resources.sprite_data import RoomSprites
from zilliandomizer.low_resources.sprite_types import AutoGunSub, BarrierSub, SpriteType
from zilliandomizer.np_sprite_manager import NPSpriteManager
from zilliandomizer.room_gen.aem import AlarmEntranceManager
from zilliandomizer.room_gen.common import BOT_LEFT, Coord, EdgeDoors, RoomData, coord_to_pixel
from zilliandomizer.room_gen.maze import Cell, Grid, MakeFailure
from zilliandomizer.room_gen.sprite_placing import alarm_places, auto_gun_places, barrier_places, choose_alarms
from zilliandomizer.terrain_modifier import TerrainModifier
from zilliandomizer.utils import make_loc_name, make_reg_name
from zilliandomizer.logger import Logger

floor_sprite_types = (
    SpriteType.mine,
    SpriteType.enemy,
    # moving falling enemies to the floor
    # because it's more complex to find a place for them to fall from
    # TODO: implement falling enemies
    SpriteType.falling_enemy
)


class RoomGen:
    """
    Anything else modifying terrain needs to be done before initializing this object,
    because this could use all of the space for terrain.
    """
    tc: TerrainModifier
    sm: NPSpriteManager
    aem: AlarmEntranceManager
    _logger: Logger
    _skill: int
    """ from options """

    _canisters: Dict[int, List[Tuple[Coord, float]]]
    """ placed canisters { map_index: [(Coord, jump_blocks_required), ...] } """

    pudding_cans: Set[int]
    """ which map indexes have a can in the pudding """

    _computers: Dict[int, Tuple[Coord, float]]
    """ placed computers { map_index: (Coord, jump_blocks_required) } """

    _rooms: Dict[int, float]
    """ rooms generated {map_index: jump_blocks} """

    _alarm_rooms: FrozenSet[int]
    """ rooms that can have alarm lines """

    _gen_rooms: Mapping[int, RoomData]
    """ data specifying what to generate - `{ map_index: RoomData }` """

    def __init__(self,
                 tc: TerrainModifier,
                 sm: NPSpriteManager,
                 aem: AlarmEntranceManager,
                 logger: Logger,
                 skill: int,
                 gen_data: Mapping[int, RoomData]) -> None:
        self.tc = tc
        self.sm = sm
        self.aem = aem
        self._logger = logger
        self._skill = skill
        self._alarm_rooms = frozenset(ALARM_ROOMS)
        self._gen_rooms = gen_data

        # testing
        # logger.spoil_stdout = True
        # logger.debug_stdout = True

    def reset(self) -> None:
        self._canisters = {}
        self.pudding_cans = set()
        self._computers = {}
        self._rooms = {}

    def generate_all(self, map_index_2_jump_level: Dict[int, int]) -> None:
        # TODO: I haven't tested the tc save state and success loop yet
        self.tc.save_state()
        self.sm.save_state()
        self.reset()

        # so the top rooms don't always have more space than the bottom
        shuffled_gen_rooms = list(self._gen_rooms.keys())
        shuffle(shuffled_gen_rooms)

        # testing code to make sure the last room can be generated if it's a split room
        # I was worried that it would run out of space and fail generation.
        # But a few samples had no problem generating the last room.
        #
        # last = self._gen_rooms[shuffled_gen_rooms[-1]]
        # if last.split_dip_entrance is None:
        #     exit()
        # assert last.split_dip_entrance == last.exits[-1]
        # if all(e[0] == last.exits[0][0] for e in last.exits[:-1]):
        #     print("all on same level")
        #     exit()

        # TODO: better source of this information, instead of
        # magic number that isn't right now that I've change GEN_ROOMS
        # (After more looking into this, it's not the calculation that
        #  I thought it was, so I don't know what it's safe to change to.
        #  Maybe the reason it's less is so that randomized alarms
        #  still have wiggle room. So maybe this 59 per room is ok.)
        """
        >>> 0x120da - 0x10ef0  # all the rom space for rooms
        4586
        >>> 4586 / 77  # all the rooms
        59.55844155844156
        """
        TOTAL_SPACE_LIMIT = len(self._gen_rooms) * 59
        success = False  # generated all rooms without going over the byte limit
        while not success:
            self._logger.spoil("generating rooms...")
            total_space_taken = 0
            for i, map_index in enumerate(shuffled_gen_rooms):
                print(f"generating room {i + 1} / {len(self._gen_rooms)}")
                jump_block_ability = 2 if map_index_2_jump_level[map_index] == 1 else (
                    2.5 if map_index_2_jump_level[map_index] == 2 else 3
                )

                n_rooms_remaining = len(self._gen_rooms) - i
                space_remaining = TOTAL_SPACE_LIMIT - total_space_taken
                space_target = space_remaining / n_rooms_remaining
                # print(f"remain {n_rooms_remaining}  space {space_remaining}  target {space_target}")
                # need to keep size limit above around 45
                # That's the number of bytes required to encode a room
                # that can be traversed from bottom to top.
                limit_to_reserve_space = space_remaining - (n_rooms_remaining - 1) * 45
                scaling_pad_on_target = space_target + (20 * (n_rooms_remaining - 1) / len(self._gen_rooms)) - 1

                # different types of rooms need different amounts of space
                # we shouldn't give the same amount of space to the simpler rooms
                room_heuristic_mult = 0.95  # + 0.5 * (map_index // 8) / 16
                if self._gen_rooms[map_index].split_dip_entrance:
                    room_heuristic_mult *= 1.1
                elif self._gen_rooms[map_index].dead_end_can is None:  # no dead end can and no split
                    room_heuristic_mult *= 0.95

                hard_space_limit = min(limit_to_reserve_space, scaling_pad_on_target * room_heuristic_mult)
                # print(f"save {important_space_save}  scale {scaling_pad_on_target}  hard {hard_space_limit}")
                space_taken, jump_required = self._generate_room(map_index, jump_block_ability, hard_space_limit)
                total_space_taken += space_taken
                self._logger.debug(f"{space_taken} over 59" if space_taken > 59 else f"{space_taken} under 60")

                self._rooms[map_index] = jump_required
            if self.tc.get_space() >= 0:
                success = True
            else:
                self._logger.debug(f"overused terrain memory by {-self.tc.get_space()} bytes")
                self.tc.load_state()
                self.sm.load_state()
                self.reset()

    def _make_optimized_no_softlock(self,
                                    exits: List[Coord],
                                    ends: List[Coord],
                                    map_index: int,
                                    jump_blocks: float,
                                    size_limit: float,
                                    no_space: Iterable[Coord],
                                    no_change: Iterable[Coord],
                                    edge_doors: EdgeDoors,
                                    pudding_tiles: Mapping[Coord, str]) -> Grid:
        tr = Grid(exits,
                  ends,
                  map_index,
                  self.tc,
                  self._logger,
                  self._skill,
                  no_space,
                  no_change,
                  edge_doors)
        for c, tile in pudding_tiles.items():
            y, x = c
            tr.data[y][x] = tile
        tr.make(jump_blocks, size_limit)
        if random() < 0.5:
            # I used to use this for softlock avoidance,
            # but after improving the movement adjacency function,
            # I don't need it for softlock avoidance anymore (maybe?).
            # But it makes a significantly different style of room,
            # so I include it randomly for variety.
            tr.fix_crawl_fall()
        tr.optimize_encoding()
        # place some new walkways after post-processing
        solved = False
        for _ in range(5 if tr.walkways else 1):
            if tr.walkways:
                tr.place_walkways()
            if tr.solve(jump_blocks):
                solved = True
                break
        if tr.softlock_exists():
            raise MakeFailure("softlock")
        if not solved:
            # This is expected to happen changing walkways after optimization
            # self._logger.warn("WARNING: room generation post-processing removed navigability")
            raise MakeFailure("post-proc broke room")
        return tr

    def _generate_split(
        self,
        map_index: int,
        jump_blocks: float,
        size_limit: float
    ) -> Tuple[
        List[Coord],  # exits
        List[Coord],  # ends
        Iterable[Coord],  # no space
        Iterable[Coord],  # no_change
        Mapping[Coord, str]  # pudding_tiles
    ]:
        """ returns (the length of the compressed room data, jump blocks required to traverse) """

        def get_ninth(y: int, x: int) -> int:
            """ with the room divided into 9 sections, which section is this coordinate in """
            return (y // 2) * 3 + (x // 5)

        this_room = self._gen_rooms[map_index]
        exits = this_room.exits[:]
        dip_entrance = this_room.split_dip_entrance
        assert dip_entrance
        entrance_ninth = get_ninth(*dip_entrance)
        pudding_ninths = [
            get_ninth(*exit_)
            for exit_ in exits
            if exit_ != dip_entrance
        ]
        assert not any(ninth == 4 for ninth in pudding_ninths + [entrance_ninth]), (
            f"entrance into middle of room? {this_room=}"
        )
        dipped_ninths = [4, entrance_ninth]

        # from entrance_ninth, walk around both directions until hitting a pudding ninth

        def go_a_direction(seq: Sequence[int]) -> None:
            i = seq.index(entrance_ninth) + 1
            while seq[i] not in pudding_ninths:
                dipped_ninths.append(seq[i])
                i += 1

        clockwise = (0, 1, 2, 5, 8, 7, 6, 3) * 2
        go_a_direction(clockwise)
        go_a_direction(tuple(reversed(clockwise)))

        assert all(pudding_ninth not in dipped_ninths for pudding_ninth in pudding_ninths)
        assert all(dipped_ninth not in pudding_ninths for dipped_ninth in dipped_ninths)

        pudding_ninths = [n for n in range(9) if n not in dipped_ninths]
        assert 4 not in pudding_ninths

        assert all(pudding_ninth not in dipped_ninths for pudding_ninth in pudding_ninths)
        assert all(dipped_ninth not in pudding_ninths for dipped_ninth in dipped_ninths)

        # make ends for dipped section
        ends = [dip_entrance]

        lowest_dipped_ninth_y = max(dipped_ninth // 3 for dipped_ninth in dipped_ninths)
        all_lowest_dipped_ninths = [
            n
            for n in range(lowest_dipped_ninth_y * 3, lowest_dipped_ninth_y * 3 + 3)
            if n in dipped_ninths
        ]
        bottom_left_ninth = all_lowest_dipped_ninths[0]
        bottom_right_ninth = all_lowest_dipped_ninths[-1]
        bottom_left_x = (bottom_left_ninth % 3) * 5
        bottom_right_x = (bottom_right_ninth % 3) * 5 + 2
        bottom_y = (bottom_left_ninth // 3) * 2 + 1
        ends.append((bottom_y, bottom_left_x))
        ends.append((bottom_y, bottom_right_x))

        # I previously added a top end unconditionally,
        # but that was costing too much rom data space.
        if all(end[0] == bottom_y for end in ends):
            highest_dipped_ninth_y = min(dipped_ninth // 3 for dipped_ninth in dipped_ninths)
            all_highest_dipped_ninths = [
                n
                for n in range(highest_dipped_ninth_y * 3, highest_dipped_ninth_y * 3 + 3)
                if n in dipped_ninths
            ]
            top_left_ninth = all_highest_dipped_ninths[0]
            top_right_ninth = all_highest_dipped_ninths[-1]
            top_left_x = (top_left_ninth % 3) * 5
            top_right_x = (top_right_ninth % 3) * 5 + 2
            top_y = (top_left_ninth // 3) * 2 + 1
            top_x = top_left_x if random() < 0.5 else top_right_x
            ends.append((top_y, top_x))

        # which grid spaces to not change
        no_change: Set[Coord] = set()
        no_space: Set[Coord] = set()
        pudding_tiles: Dict[Coord, str] = {}
        for n in pudding_ninths:
            top_y = (n // 3) * 2
            left_x = (n % 3) * 5
            for y in range(top_y, top_y + 2):
                for x in range(left_x - 1, left_x + 5):
                    if x >= 0 and x < 14:
                        coord = (y, x)
                        no_change.add(coord)
                        no_space.add((y - 1, x))
                        if x % 5 != 4:  # if not a ninth boundary
                            if y & 1:
                                pudding_tiles[coord] = Cell.floor
                            else:
                                pudding_tiles[coord] = Cell.space

        # open up boundaries between pudding tiles
        if 0 in pudding_ninths and 1 in pudding_ninths:
            pudding_tiles[(0, 4)] = Cell.space
            pudding_tiles[(1, 4)] = Cell.floor
        if 1 in pudding_ninths and 2 in pudding_ninths:
            pudding_tiles[(0, 9)] = Cell.space
            pudding_tiles[(1, 9)] = Cell.floor
        if 2 in pudding_ninths and 5 in pudding_ninths:
            pudding_tiles[(1, 10)] = Cell.space
            pudding_tiles[(1, 11)] = Cell.space
        if 5 in pudding_ninths and 8 in pudding_ninths:
            pudding_tiles[(3, 10)] = Cell.space
        if 7 in pudding_ninths and 8 in pudding_ninths:
            pudding_tiles[(4, 9)] = Cell.space
            pudding_tiles[(5, 9)] = Cell.floor
        if 6 in pudding_ninths and 7 in pudding_ninths:
            pudding_tiles[(4, 4)] = Cell.space
            pudding_tiles[(5, 4)] = Cell.floor
        if 3 in pudding_ninths and 6 in pudding_ninths:
            pudding_tiles[(3, 3)] = Cell.space
        if 0 in pudding_ninths and 3 in pudding_ninths:
            pudding_tiles[(1, 2)] = Cell.space
            pudding_tiles[(1, 3)] = Cell.space

        return [dip_entrance], ends, no_space, no_change, pudding_tiles

    def _generate_room(self,
                       map_index: int,
                       jump_blocks: float,
                       size_limit: float) -> Tuple[int, float]:
        """ returns (the length of the compressed room data, jump blocks required to traverse) """
        this_room = self._gen_rooms[map_index]

        pudding_tiles: Mapping[Coord, str]
        if this_room.split_dip_entrance:
            exits, ends, no_space, no_change, pudding_tiles = self._generate_split(map_index, jump_blocks, size_limit)
            second_candidate_for_elevation = False
        else:
            exits = this_room.exits[:]  # real exits
            ends = exits[:]  # places I want to be able to get to

            # special case row 14 col 1 - because of the exit-only door
            # This must be done before these random ends are added,
            # because a random end might conflict with this one.
            if map_index == 113:
                if BOT_LEFT not in ends:
                    ends.append(BOT_LEFT)

            # make sure traversal doesn't just stay in one corner of the room
            if not any(end[1] < 5 for end in ends):
                ends.append((randrange(1, 6), 0))
            if not any(end[1] > 8 for end in ends):
                ends.append((randrange(1, 6), 12))
            if not any(end[0] > 4 for end in ends):
                ends.append((5, randrange(5, 8)))
            if not any(end[0] < 3 for end in ends):
                if random() < 0.5:
                    ends.append((1, randrange(0, 13)))

            # If all the ends are on the bottom, I want an extra chance to get high goables
            second_candidate_for_elevation = all(end[0] > 2 for end in ends)

            no_space = this_room.no_space
            no_change = ()
            pudding_tiles = {}

        g: Optional[Grid] = None
        primary_placed: List[Coord] = []
        pudding_placed: List[Coord] = []
        alarm_blocks: Dict[int, Literal['v', 'h', 'n']] = {}

        fail_count = 0
        while not g:
            try:
                candidate = self._make_optimized_no_softlock(
                    exits, ends, map_index, jump_blocks, size_limit,
                    no_space, no_change, this_room.edge_doors, pudding_tiles
                )
                candidate_goables = candidate.get_goables(jump_blocks)
                if second_candidate_for_elevation:
                    # lowest y coordinate is highest elevation
                    highest = min(c[0] for c in candidate_goables)
                    if highest > 1:
                        candidate_2 = self._make_optimized_no_softlock(
                            exits, ends, map_index, jump_blocks, size_limit,
                            no_space, no_change, this_room.edge_doors, pudding_tiles
                        )
                        candidate_2_goables = candidate_2.get_goables(jump_blocks)
                        highest_2 = min(c[0] for c in candidate_2_goables)
                        if highest_2 < highest:
                            candidate = candidate_2
                            candidate_goables = candidate_2_goables
                # TODO: find out which exits require jump 2.5, 3
                standing = [g for g in candidate_goables if g[2]]
                primary_placeables = [(y, x) for y, x, _ in standing if not candidate.in_exit(y, x)]
                location_count = map_index_to_loc_count[map_index] - (1 if this_room.dead_end_can else 0)
                sprites = self.sm.get_room(map_index)
                room_floor_sprite_count = sum(s.type[0] in floor_sprite_types for s in sprites)

                pudding_can = False
                # only place anything in pudding if we have more than 2 ninths of pudding
                if len(pudding_tiles) > 20:
                    # some magic numbers I experimented with in a calculator
                    # to decide how many things to put in pudding
                    #  - might be able to lower the divisor for more
                    can_place_in_pudding = (len(pudding_tiles) - 14) // 6
                    if location_count > 4:
                        pudding_can = True
                    pudding_floor_sprite_count = min((can_place_in_pudding - pudding_can), room_floor_sprite_count)
                    will_place_in_pudding = pudding_floor_sprite_count + pudding_can
                    pudding_goables = candidate.get_goables(jump_blocks, this_room.exits[0])
                    pudding_standing = [g for g in pudding_goables if g[2]]
                    pudding_placeables = [
                        (y, x)
                        for y, x, _ in pudding_standing
                        if not candidate.in_exit(y, x, this_room.exits)
                    ]
                    self._logger.debug(f"{pudding_placeables=}")
                    if len(pudding_placeables) < will_place_in_pudding:
                        raise MakeFailure(f"Not enough room in {map_index=} pudding to place {will_place_in_pudding}")
                    pudding_placed = sample(pudding_placeables, will_place_in_pudding)
                else:
                    will_place_in_pudding = 0
                    pudding_floor_sprite_count = 0

                primary_floor_sprite_count = room_floor_sprite_count - pudding_floor_sprite_count
                primary_placeable_count = (
                    (location_count - pudding_can) +
                    this_room.computer +
                    primary_floor_sprite_count
                )
                self._logger.debug(
                    f"need to place {primary_placeable_count} in room {map_index} primary region and "
                    f"{will_place_in_pudding} in pudding region, including {pudding_can=} with {len(pudding_tiles)=}"
                )
                if len(primary_placeables) < primary_placeable_count:
                    raise MakeFailure("not enough places to put things")
                if primary_placeable_count > 0:
                    # take 2 samples, and choose whichever has higher coords
                    # (to counter the tendency of putting most on the lowest level)
                    placed_1 = sample(primary_placeables, primary_placeable_count)
                    placed_2 = sample(primary_placeables, primary_placeable_count)
                    sum_1 = sum(p[0] for p in placed_1)
                    sum_2 = sum(p[0] for p in placed_2)
                    primary_placed = placed_1 if sum_1 < sum_2 else placed_2
                alarm_blocks = self.place(
                    primary_placed, sprites, map_index, candidate, this_room.dead_end_can, pudding_placed, pudding_can
                )

                if map_index == 0x10:
                    # This is part of making sure 1st sphere is not empty.
                    placed_cans = self._canisters[map_index]
                    assert len(placed_cans) == 5, f"{map_index=} {len(placed_cans)=}"
                    good = any(can[1] <= 2 for can in placed_cans)
                    # can get to at least 1 can without any jump levels
                    if not good:
                        raise MakeFailure("need location in r02c0 that doesn't require jump levels")

                compressed = candidate.to_room_data(alarm_blocks)
                if len(compressed) > size_limit:
                    raise MakeFailure("over size limit")
                if pudding_can:
                    self.pudding_cans.add(map_index)
                g = candidate
                # testing - TODO: make unit test for Grid.no_space
                # if map_index in (0x4b, 0x21):
            except MakeFailure:
                print(".", end="")
                fail_count += 1
                if fail_count > 1500:
                    raise MakeFailure("too many failures in Zillion room generation - try generating again"
                                      f" - index {map_index} sl {size_limit}")
        print()

        jump_blocks_required = 2 if g.solve(2) else (2.5 if g.solve(2.5) else 3)
        # require jumping to computer
        if map_index in self._computers:
            computer_jump = self._computers[map_index][1]
            jump_blocks_required = max(jump_blocks_required, computer_jump)
        # TODO: unit test to make sure it will see if I can't jump to the computer to open the door

        # testing
        # TODO: make unit test for Grid.no_space
        # if map_index in (0x4b, 0x21):
        if self._logger.debug_stdout:  # check to reduce processing of creating the map string
            self._logger.debug("map_index {:#02x}".format(map_index))
            self._logger.debug(f"jump blocks required {jump_blocks_required}")
            self._logger.debug(g.map_str(primary_placed + pudding_placed))
        compressed = g.to_room_data(alarm_blocks)
        self.tc.set_room(map_index, compressed)
        return len(compressed), jump_blocks_required

    def place(self,
              primary_coords: List[Coord],
              sprites: RoomSprites,
              map_index: int,
              grid: Grid,
              dead_end_can: Union[Coord, None],
              pudding_placed: List[Coord],
              pudding_can: bool) -> Dict[int, Literal['v', 'h', 'n']]:
        """
        place the things that need to be placed in this room

        length of primary_coords + pudding_placed should be the sum (
            the number of floor sprites in the non-player sprite table
            + (the number of canisters in the room - (1 if this_room.dead_end_can else 0))
            + 1 if there's a computer in the room
        )

        For split rooms, the `pudding_placed` list has coordinates from the pudding.
        Floor sprites will be taken from the end of the list.
        There needs to be enough coordinates from dipped for all the canisters and the computer
        (taken from the beginning of the list).

        returns alarm block data (input to `Alarms.add_alarms_to_room_terrain_bytes`)
        """
        # TODO: possible uncompletable seed: Make sure I can get to 2 places
        # in the height of the lowest canister.
        # (This might be solved with new end adding near the beginning of _generate_room)

        all_floor_placements_pudding_at_end = primary_coords + pudding_placed
        full_room_exits = set(self._gen_rooms[map_index].exits)  # set for __contains__ performance
        agp = auto_gun_places(grid, full_room_exits)
        bp = barrier_places(grid, all_floor_placements_pudding_at_end, full_room_exits)
        # last index will be saved for pudding_can
        end_cursor = len(all_floor_placements_pudding_at_end) - (1 + pudding_can)
        for sprite in sprites:
            if sprite.type[0] in floor_sprite_types:
                # TODO: can I make it so it's always possible to jump over mines?
                y, x = coord_to_pixel(all_floor_placements_pudding_at_end[end_cursor])
                end_cursor -= 1
                if sprite.type[0] == SpriteType.mine:
                    y += 0x10
                elif sprite.type[0] == SpriteType.falling_enemy:
                    sprite.type = (SpriteType.enemy, sprite.type[1])
                sprite.x = x
                sprite.y = y
            elif sprite.type[0] == SpriteType.barrier:
                if len(bp.bars):
                    bar_place = bp.bars.pop()
                    new_subtype = (
                        (BarrierSub.hor_2, BarrierSub.hor_4)[bar_place.length - 1]
                        if bar_place.horizontal
                        else (BarrierSub.ver_4, BarrierSub.ver_8)[bar_place.length - 1]
                    )

                    sprite.type = (sprite.type[0], new_subtype)
                    y, x = coord_to_pixel(bar_place.c)
                    if bar_place.horizontal:
                        y += 0x20  # bottom of tile
                    else:  # vertical
                        y += 8
                        x += 8 * randrange(2)  # either left or right side of larger tile
                        # TODO: if one side is next to a wall, move x away from wall
                else:  # didn't find any good place to put a bar
                    # This mine will show up in next room,
                    # while screen scrolls to it going down elevator.
                    # But then it disappears when arriving (stop scrolling)
                    # and I didn't find any way to interact with it.
                    # So it's not a bad way of disposing of a sprite.
                    sprite.type = (SpriteType.mine, 0x00)
                    y = 0xbc  # half off screen
                    x = 0xa0  # where elevators don't reach
                    # TODO: need a better solution in case I change location of elevators
                    self._logger.debug(f"not enough good places for barrier in room {map_index}")
                sprite.y = y
                sprite.x = x
            elif sprite.type[0] == SpriteType.auto_gun:
                # TODO: can I avoid having them move over doors?
                # (I already avoid placing them on doors, but they can still move.)

                # TODO: more than 4 guns in a row makes some of them invisible (r07c4)

                subtype = sprite.type[1]
                if subtype in (AutoGunSub.down, AutoGunSub.down_move):
                    if len(agp.down):
                        c = agp.down.pop()
                        y, x = coord_to_pixel(c)
                        y += 8
                    else:
                        y = 0
                        x = randrange(0x10, 0xe1)
                elif subtype in (AutoGunSub.right, AutoGunSub.right_move):
                    if len(agp.right):
                        c = agp.right.pop()
                        y, x = coord_to_pixel(c)
                        y += 16
                    else:
                        y = randrange(0x48, 0x69)
                        x = 0x10
                else:  # left facing
                    if len(agp.left):
                        c = agp.left.pop()
                        y, x = coord_to_pixel(c)
                        y += 16
                    else:
                        y = randrange(0x48, 0x69)
                        x = 0xe0
                sprite.x = x
                sprite.y = y
            else:
                self._logger.warn(f"sprite type {sprite.type[0]} unhandled in room {map_index}")
        goables_2 = grid.get_standing_goables(2)
        goables_25 = grid.get_standing_goables(2.5)
        begin_cursor = 0
        if self._gen_rooms[map_index].computer:
            y, x = primary_coords[begin_cursor]
            # to make sure computer can be accessed to traverse room
            state = (y, x, True)
            jump = 2 if state in goables_2 else (
                2.5 if state in goables_25 else 3
            )
            self._computers[map_index] = (primary_coords[begin_cursor], jump)
            begin_cursor += 1
        # canisters
        cans: List[Tuple[Coord, float]] = []
        for coord in primary_coords[begin_cursor:end_cursor + 1]:
            y, x = coord
            state = (y, x, True)
            jump = 2 if state in goables_2 else (
                2.5 if state in goables_25 else 3
            )
            cans.append((coord, jump))
        self._canisters[map_index] = cans
        self._logger.debug(f"{map_index=} placed {len(cans)=} {begin_cursor=} {end_cursor=} {pudding_can=}")
        if pudding_can:
            # jump_blocks 0 assuming no interesting terrain in pudding
            self._canisters[map_index].append((all_floor_placements_pudding_at_end[-1], 0))
        if dead_end_can:
            # Room traversal to all exits covers the jump requirement for this (in the "enter" region).
            # See doc of `get_jump_blocks_required`.
            self._canisters[map_index].append((dead_end_can, 0))

        self.sm.set_room(map_index, sprites)

        if map_index in self._alarm_rooms:
            enemy_level = 0 if map_index < 0x20 else (
                1 if map_index < 0x50 else 2
            )
            if self.aem.is_ceiling(map_index):
                for x, i in self.aem.get_ceiling_entrances(enemy_level):
                    col = x // 16 - 1
                    if grid.data[0][col] == Cell.space:
                        self._logger.debug(f"map index {map_index} alarm entrance col {col}")
                        self.aem.indexes[map_index] = i
                        # If there are no spaces in ceiling for alarm entrance, aem index doesn't change,
                        # so it will still be pointing at one of the ceiling entrances.
                        # (The order of the ceiling entrance data doesn't change.)
                        break
            else:
                edge_doors = grid.get_edge_doors()
                if edge_doors:
                    # not vanilla edge doors
                    # change from door entrance to ceiling entrance
                    chosen_index = -1
                    for x, i in self.aem.get_ceiling_entrances(enemy_level):
                        if chosen_index == -1:
                            # default in case we don't find better
                            chosen_index = i
                        col = x // 16 - 1
                        if grid.data[0][col] == Cell.space:
                            self._logger.debug(f"map index {map_index} alarm entrance col {col}")
                            chosen_index = i
                            break
                    assert chosen_index != -1
                    self.aem.indexes[map_index] = chosen_index

            mu = 0.25 * (map_index // 8) + 0.75
            count = 0
            while count < 1:
                count = round(gauss(mu, 1))
            ap = alarm_places(grid, all_floor_placements_pudding_at_end)
            return choose_alarms(ap, count)
        else:
            return {}

    def make_locations(self) -> Dict[str, Location]:
        # original = make_locations()
        locations: Dict[str, Location] = {}
        generated_rooms: Set[str] = set()  # 5-letter base region name ("r04c5")

        for map_index, placed in self._canisters.items():
            assert len(placed) < 8, f"{map_index=} {placed=}"
            reg_name = make_reg_name(map_index)
            generated_rooms.add(reg_name)
            for can in placed:
                coord, jump_blocks = can
                jump_level = 3 if jump_blocks == 3 else (
                    2 if jump_blocks == 2.5 else 1
                )
                y, x = coord_to_pixel(coord)
                loc_name = make_loc_name(map_index, y, x)
                locations[loc_name] = Location(loc_name, Req(gun=1, jump=jump_level))

        # copy locations from rooms that I didn't generate
        vanilla_locations = make_locations()
        for loc_name, loc in vanilla_locations.items():
            if loc_name[:5] not in generated_rooms:
                locations[loc_name] = loc
        locations["main"] = locations["r10c5y98x18"]  # alias
        return locations

    def get_computer(self, map_index: int) -> bytes:
        """ see doc in utils for format of computer location data """
        if map_index in self._computers:
            y, x = coord_to_pixel(self._computers[map_index][0])
            v = y >> 3
            h = x >> 3
            tr = (v << 6) | (h << 1)
            return tr.to_bytes(2, 'little')
        else:
            return b'\xff'

    def get_modified_rooms(self) -> FrozenSet[int]:
        return frozenset(self._rooms)

    def get_jump_blocks_required(self, map_index: int) -> float:
        """
        For the given `map_index`, returns the number of large tiles in height that you need
        to be able to jump in order to traverse to all the exits.

        For the dead end canister rooms, this is important because
        the canister itself doesn't have the jump requirement on it.

        In split rooms, this only applies to the dipped section,
        and is therefore useless in those rooms,
        since there are no exits to go to from the dipped section.
        The pudding section should always require only 2 jump blocks.

        returns 0 if this map index wasn't generated
        """
        if map_index in self._rooms:
            return self._rooms[map_index]
        return 0
