from collections import defaultdict, deque
from typing import Container, Dict, Iterable, List, Mapping, Set

from zilliandomizer.logic_components.region_data import MapBuilder
from zilliandomizer.map_gen.base_maker import BaseMaker, Node
from zilliandomizer.map_gen.map_data import pc_no_doors, red_right_no_doors

_red_exits = {Node(1, 0), Node(3, 0), Node(4, 0)}

_pc_exits = {Node(0, 5)}

_dipped_suffix = "unlocker"
_pudding_suffix = "passage"


def make_regions_bm(bm: BaseMaker,
                    mb: MapBuilder,
                    node_no_doors: Iterable[Node],
                    pre_entrance_region: str,
                    start_node: Node,
                    exits: Container[Node],
                    splits: Mapping[Node, Node],
                    pudding_cans: Container[int]) -> None:
    """ `pudding_cans` is which nodes have a can in the pudding """

    def reg_name(node: Node) -> str:
        row, col = node
        map_row = row + bm.row_offset
        map_col = col + bm.col_offset
        return f"r{map_row:02}c{map_col}"

    no_doors = set(reg_name(node) for node in node_no_doors)
    no_doors.add(pre_entrance_region)

    entrance_name = reg_name(start_node)

    parents: Dict[str, str] = {entrance_name: pre_entrance_region}
    """ key is only the base region name r00c0, value might be more r00c0passage """

    split_doors_to_correct_later: Dict[str, List[str]] = defaultdict(list)
    """
    doors from key to values need to be corrected later
    with door value (key - pudding suffix + dipped suffix)
    """

    done: Set[Node] = set()
    q = deque([start_node])

    while len(q):
        node = q.popleft()
        if node in done:
            continue
        done.add(node)

        row, col = node
        map_row = row + bm.row_offset
        map_col = col + bm.col_offset
        region_name_base = reg_name(node)
        adjs = list(bm.adjs(node))
        dead_end = (len(adjs) == 1) and (node not in exits) and (node not in splits.values())
        computer_opens_door = region_name_base not in no_doors
        dead_end_door = dead_end and computer_opens_door

        parent = parents[region_name_base]
        # This `parent` could be a pudding_name will be checked in no_doors,
        # which will always be false
        # since pudding names don't get put in no_doors.
        # This is ok since we only allow rooms with doors to be split.

        split = node in splits
        assert not (split and dead_end_door)
        logical_region_name = region_name_base

        if dead_end_door:
            locations_in_room = [loc_name for loc_name in mb.reg_name_to_loc_name[region_name_base]]
            assert locations_in_room[-1][6:8] == "18", f"locked location should be top row {locations_in_room}"
            mb.split(map_row, map_col, {
                "enter": locations_in_room[:-1],
                "locked": [locations_in_room[-1]],
            }, True)
            enter_name = region_name_base + "enter"
            locked_name = region_name_base + "locked"
            if parent in no_doors:
                mb.r[parent].to(mb.r[enter_name])
            else:  # parent has door
                mb.r[parent].to(mb.r[enter_name], door=True)
            if parent.endswith(_pudding_suffix):
                split_doors_to_correct_later[parent].append(enter_name)
            mb.r[enter_name].to(mb.r[locked_name], door=True)
        elif split:
            """ example split from vanilla

            mb.split(13, 3, {
                "s": [              # unlocker
                    "r13c3y58x30",
                    "r13c3y58xc0",
                    "r13c3y98xe0",
                    "r13c3y58xd0",
                    "r13c3y58xe0",
                ],
                "n": [              # passage

                ],
            }, True)

            mb.r["r14c3"].to(mb.r["r13c3s"], door=True)  # dipper to dipped
            mb.r["r13c4"].to(mb.r["r13c3n"], door=True)  # pudding parent to pudding
            mb.r["r13c3n"].to(mb.r["r13c2"], door=mb.r["r13c3s"].door)  # pudding to pudding child
            """
            locations_in_room = [loc_name for loc_name in mb.reg_name_to_loc_name[region_name_base]]
            map_index = map_row * 8 + map_col
            if map_index in pudding_cans:
                dipped_locations = locations_in_room[:-1]
                pudding_locations = locations_in_room[-1:]
            else:
                dipped_locations = locations_in_room
                pudding_locations = []
            mb.split(map_row, map_col, {
                _pudding_suffix: pudding_locations,
                _dipped_suffix: dipped_locations,
            }, True)
            pudding_name = region_name_base + _pudding_suffix
            logical_region_name = pudding_name
            if parent in no_doors:
                mb.r[parent].to(mb.r[pudding_name])
            else:  # parent has door
                mb.r[parent].to(mb.r[pudding_name], door=True)
            if parent.endswith(_pudding_suffix):
                assert False, "not pudding [sic] two split rooms next to each other"
                split_doors_to_correct_later[parent].append(pudding_name)  # type: ignore[unreachable]
        else:  # not divided
            mb.room(map_row, map_col, len(mb.reg_name_to_loc_name[region_name_base]), computer_opens_door)
            if parent in no_doors:
                mb.r[parent].to(mb.r[region_name_base])
            else:  # parent has door
                mb.r[parent].to(mb.r[region_name_base], door=True)
            if parent.endswith(_pudding_suffix):
                split_doors_to_correct_later[parent].append(region_name_base)

        for adj in adjs:
            if adj not in done:
                child_name = reg_name(adj)
                parents[child_name] = logical_region_name
                q.append(adj)

    for split_node, dipper in splits.items():
        dipper_name = reg_name(dipper)
        split_base_name = reg_name(split_node)
        dipped_name = split_base_name + _dipped_suffix
        if dipper_name in no_doors:
            mb.r[dipper_name].to(mb.r[dipped_name])
        else:  # dipper has door
            mb.r[dipper_name].to(mb.r[dipped_name], door=True)

    for pudding_name, children in split_doors_to_correct_later.items():
        assert pudding_name.endswith(_pudding_suffix)
        dipped_name = pudding_name[:-len(_pudding_suffix)] + _dipped_suffix
        for child in children:
            for connecting_region, req in mb.r[pudding_name].connections.items():
                if connecting_region.name == child:
                    req.door = mb.r[dipped_name].door
                    break  # next child
            else:  # didn't break
                assert False, f"didn't find region with name {child} from {pudding_name}"


def make_red_right_bm(bm: BaseMaker, mb: MapBuilder, splits: Mapping[Node, Node]) -> None:
    assert bm.height == 5 and bm.width == 5, f"{bm.height=} {bm.width=}"
    node_no_doors = red_right_no_doors
    pre_entrance_region = "between_blue_red"
    start_node = Node(0, 3)
    exits = _red_exits

    make_regions_bm(bm, mb, node_no_doors, pre_entrance_region, start_node, exits, splits, ())

    mb.hall("red_elevator")

    mb.r["r09c3"].to(mb.r["red_elevator"], door=True)
    mb.r["r08c3"].to(mb.r["red_elevator"], door=True)
    mb.r["r06c3"].to(mb.r["red_elevator"], door=True)


def make_paperclip_bm(
    bm: BaseMaker, mb: MapBuilder, splits: Mapping[Node, Node], pudding_cans: Container[int]
) -> None:
    assert bm.height == 7 and bm.width == 8, f"{bm.height=} {bm.width=}"
    node_no_doors = pc_no_doors
    pre_entrance_region = "big_elevator"
    start_node = Node(0, 0)
    exits = _pc_exits

    make_regions_bm(bm, mb, node_no_doors, pre_entrance_region, start_node, exits, splits, pudding_cans)

    assert "r10c5" in mb.r
