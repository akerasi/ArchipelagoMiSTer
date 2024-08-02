from typing import Dict, Iterable, List, Mapping, Sized, Tuple, Union

from zilliandomizer.map_gen.base import Base
from zilliandomizer.map_gen.base_maker import BaseMaker, Node
from zilliandomizer.map_gen.door_decider import DE, Desc, make_edge_descriptions
from zilliandomizer.room_gen.common import BOT_LEFT, Coord, EdgeDoors, RoomData, TOP_LEFT, TOP_RIGHT
from zilliandomizer.room_gen.data import GEN_ROOMS

_red_right_generate = {
    0x2b, 0x2c, 0x2d,       0x2f,
    0x33, 0x34,       0x36, 0x37,
    0x3b, 0x3c, 0x3d, 0x3e, 0x3f,
    0x43, 0x44, 0x45, 0x46, 0x47,
    0x4b, 0x4c, 0x4d,       0x4f,
}

_pc_generate = {
    0x51, 0x52, 0x53, 0x54,
    0x59, 0x5a, 0x5b, 0x5c, 0x5d, 0x5e,
    0x61, 0x62, 0x63, 0x64, 0x65, 0x66,
    0x69, 0x6a, 0x6b, 0x6c, 0x6d, 0x6e,
    0x71, 0x72, 0x73, 0x74, 0x75, 0x76,
    0x82, 0x7a, 0x7b, 0x7c, 0x7d, 0x7e,
}

# TODO: logic for whole base - missing red left and blue
_has_computer_no_door = {
    79,  # bottom right red
    81, 89, 97, 113,  # left side of paperclip
}

_split_rooms = {
    44, 68,  # Apple, red scope
    81, 83, 84,
    89, 93, 94,
    101, 102,
    105, 107, 109, 110,
    113, 118,
    122, 123, 126,
    130,
}
""" rooms that I don't generate in map_gen rooms, but do generate in map_gen full """


def room_data_exits_from_descs(descs: Iterable[Desc]) -> Tuple[List[Coord], EdgeDoors, Union[Coord, None]]:
    """
    `(exits, edge_doors, dip_entrance)` (parameters to `RoomData`)

    first value in `descs` should be the entrance
    """
    out: List[Coord] = []
    edge_doors: Tuple[List[int], List[int]] = ([], [])
    dip_entrance: Union[Coord, None] = None
    for desc in descs:
        if desc.de is DE.door:
            if desc.x == 0x08:
                x = 0
            else:
                assert desc.x == 0xf0, f"{desc.x=}"
                x = 12
            y = desc.y + 1
            edge_doors[x // 12].append(y)
        else:
            assert desc.de is DE.elevator  # TODO: assert_type()
            x = (desc.x >> 4) - 1
            if desc.y == 0:
                y = 1
            else:
                assert desc.y == 5, f"{desc=}"
                y = 5
        assert y >= 0 and x >= 0, f"{descs=}"
        out.append((y, x))
        if desc.dip_entrance:
            assert dip_entrance is None, f"multiple dip entrances? {descs=}"
            dip_entrance = (y, x)
    return out, edge_doors, dip_entrance


def make_room_gen_data(base: Base, pc_splits: Mapping[Node, Node]) -> Dict[int, RoomData]:
    out = GEN_ROOMS.copy()

    _add_to_gen_rooms(out, base.red, {})
    _add_to_gen_rooms(out, base.paperclip, pc_splits)

    return out


def _add_to_gen_rooms(out: Dict[int, RoomData], bm: BaseMaker, splits: Mapping[Node, Node]) -> None:
    edge_descriptions = make_edge_descriptions(bm, splits)

    for row in range(bm.row_offset, bm.row_offset + bm.height):
        for col in range(bm.col_offset, bm.col_offset + bm.width):
            map_index = row * 8 + col
            if map_index in out:
                # delete vanilla
                del out[map_index]
            if map_index not in _red_right_generate and map_index not in _pc_generate:
                continue
            node = Node(row - bm.row_offset, col - bm.col_offset)
            outs = edge_descriptions[node]
            exits, edge_doors, dip_entrance = room_data_exits_from_descs(outs.values())

            if map_index in GEN_ROOMS:
                computer = GEN_ROOMS[map_index].computer
            else:
                assert map_index in _split_rooms, f"split with computer: {map_index=}"
                computer = True

            computer_opens_door = computer and map_index not in _has_computer_no_door

            # exits to red elevator, all need space before door to prevent softlock in escape
            no_space: List[Coord]
            if map_index in {0x33, 0x43, 0x4b}:
                no_space = [(3, 0)]
                assert edge_doors
                left_edge, right_edge = edge_doors
                assert isinstance(left_edge, Sized) and len(left_edge) == 0, f"{left_edge=}"
                left_edge = [5]
                edge_doors = (left_edge, right_edge)
                # assert BOT_LEFT not in exits - this assertion not valid
                # TODO: This statement that this assertion is not valid is not valid... maybe...?
                # (Because I found out that the door will disable the elevator so it doesn't work.)
                # So maybe this assertion should come back.  ?
                exits.append(BOT_LEFT)
            else:
                no_space = []

            dead_end_can: Union[Coord, None] = None
            if len(exits) == 1:
                # dead end
                if computer_opens_door:
                    y, x = exits[0]
                    if y > 3:
                        # entrance at bottom of room
                        dead_exit = bm.random.choice((TOP_RIGHT, TOP_LEFT))
                    else:
                        # entrance at top of room
                        if x < 7:
                            dead_exit = TOP_RIGHT
                        else:
                            dead_exit = TOP_LEFT
                    exits.append(dead_exit)
                    if dead_exit == TOP_RIGHT:
                        bm.door_manager.add_door(map_index, 0, 0xd8, map_index)
                        dead_end_can = (1, 13)
                    else:
                        assert dead_exit == TOP_LEFT
                        bm.door_manager.add_door(map_index, 0, 0x20, map_index)
                        dead_end_can = dead_exit
                    assert dead_end_can

            out[map_index] = RoomData(exits, computer, no_space, edge_doors, dead_end_can, dip_entrance)
