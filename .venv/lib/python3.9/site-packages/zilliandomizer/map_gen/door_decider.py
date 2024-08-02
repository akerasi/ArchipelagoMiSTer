from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import Deque, Dict, List, Literal, Mapping, Set, Tuple, Union

from .base_maker import BaseMaker, Node
from .map_data import pc_no_doors, red_right_no_doors

_safe_elevator_x = (0x10, 0x20, 0x30, 0x60, 0x80, 0xd0, 0xd0)
"""
all elevators in vanilla are at x pixels: 10, 20, 30, 60, 80, d0
so I don't know whether it's safe to put elevators at other x coordinates

in room_gen.py, we hide extra sprites at a0, so it's not safe there

The width of the elevator is 1.5 large tiles (so e0 isn't safe).

This is a distribution to `random.choice` from, so some are listed multiple times.
"""


class Corner(Enum):
    bl = auto()
    tl = auto()
    br = auto()
    tr = auto()


class DE(Enum):
    door = auto()
    elevator = auto()
    hallway_elevator = auto()


@dataclass(frozen=True)
class Desc:
    de: DE
    y: int
    """ in door data structure units (0 - 5) """
    x: int
    """ in pixels (0x00 - 0xf0) """
    dip_entrance: bool = False
    """ whether this is a dip entrance in a split room """

    def corner_conflicts(self) -> List[Corner]:
        """ with possible conflicts (A door in a corner is not a possible conflict - only doors at 1 or 3.) """
        if self.de is DE.elevator:
            if self.y > 2:
                # bottom
                if self.x < 0x30:
                    return [Corner.bl]
                if self.x > 0xc0:
                    return [Corner.br]
                return []
            if self.y < 2:
                # top
                if self.x < 0x30:
                    return [Corner.tl]
                if self.x > 0xc0:
                    return [Corner.tr]
                return []
        elif self.de is DE.door:
            if self.y == 3:
                # bottom
                if self.x < 0x30:
                    return [Corner.bl]
                if self.x > 0xc0:
                    return [Corner.br]
                return []
            if self.y == 1:
                # top
                if self.x < 0x30:
                    return [Corner.tl]
                if self.x > 0xc0:
                    return [Corner.tr]
                return []
        else:
            assert self.de is DE.hallway_elevator  # TODO: assert_type
            return []
        return []


_red_requires_y: Dict[Node, int] = {
    Node(1, 2): 4,  # hall
    Node(4, 3): 4,  # hall
}

_pc_requires_y: Dict[Node, int] = {
    Node(1, 0): 4,
    Node(3, 0): 0,  # M-2
    Node(4, 0): 4,
    Node(5, 1): 4,
    Node(6, 1): 4,
    Node(6, 3): 4,
    Node(5, 7): 4,
    Node(4, 7): 4,
    Node(3, 7): 0,  # red card
}


_red_right_area_exits = {
    51: Desc(DE.door, 4, 0x18),
    67: Desc(DE.door, 4, 0x18),
    75: Desc(DE.door, 4, 0x18),
}


def make_edge_descriptions(bm: BaseMaker, splits: Mapping[Node, Node]) -> Dict[Node, Dict[Node, Desc]]:
    """
    choose locations of doors and elevators

    The first `Desc` in the inner `dict` is the entrance to the room (the outer `Node`).
    """
    # print(bm.map_str())

    if bm.height == 5:  # red
        parents: Dict[Node, Union[Node, None]] = {
            Node(0, 3): None,
            Node(0, 2): Node(0, 3),
            Node(0, 4): Node(0, 3),
        }
        edge_descriptions: Dict[Node, Dict[Node, Desc]] = {
            Node(0, 3): {
                Node(0, 2): Desc(DE.door, 4, 0x08),
                Node(0, 4): Desc(DE.door, 4, 0xf0),
            },
        }
        no_doors = red_right_no_doors
        requires_y = _red_requires_y
        start_node = Node(0, 3)
    else:
        assert bm.height == 7, f"{bm.height=}"  # paperclip
        parents = {
            Node(0, 0): None,
            Node(1, 0): Node(0, 0),
        }
        edge_descriptions = {
            Node(0, 0): {
                Node(1, 0): Desc(DE.hallway_elevator, 0, 0),
            },
        }
        no_doors = pc_no_doors
        requires_y = _pc_requires_y
        start_node = Node(0, 0)

    def back_to_computer(node: Node) -> int:
        """ map_index of last keyword room in path """
        back: Union[Node, None] = node
        while back in no_doors:
            back = parents[back]
        if back is None:
            return bm.prev_door
        return (back.y + bm.row_offset) * 8 + (back.x + bm.col_offset)

    for row in range(bm.row_offset, bm.row_offset + bm.height):
        for col in range(bm.col_offset, bm.col_offset + bm.width):
            map_index = row * 8 + col
            bm.door_manager.del_room(map_index)

    dippers = set(splits.values())

    done: Set[Node] = set()
    q: Deque[Node] = deque([start_node])

    while len(q):
        here = q.popleft()
        if here in done:
            continue
        done.add(here)
        row = bm.row_offset + here.y
        col = bm.col_offset + here.x
        map_index = row * 8 + col
        adjs = list(bm.adjs(here))
        parent = parents[here]
        outs = [n for n in adjs if n != parent]
        if parent:
            assert here not in edge_descriptions, f"{here=}"
            edge_descriptions[here] = {}
            in_desc = edge_descriptions[parent][here]
            entrance_y, entrance_x = get_entrance_coords(here, parent, in_desc)
            out_through_in = Desc(in_desc.de, entrance_y, entrance_x)
            edge_descriptions[here][parent] = out_through_in
            corners_used_in_this_room = out_through_in.corner_conflicts()
            if (map_index - 8) in _red_right_area_exits:
                # don't allow going up into the extended softlock avoidance door
                corners_used_in_this_room.append(Corner.tl)
            if map_index in _red_right_area_exits:
                # when the extended softlock avoidance door opens,
                # it will disable the elevator that appears in the same place
                corners_used_in_this_room.append(Corner.bl)
            for out in outs:
                if here.x < out.x:  # going to right
                    if out in splits:
                        dipper_to_out = splits[out]
                        if dipper_to_out.y > out.y:  # dipper below
                            y_choices = [0]
                        elif dipper_to_out.y < out.y:  # dipper above
                            y_choices = [4]
                        else:  # dipper coming from opposite side
                            assert dipper_to_out.x > out.x, f"{here=} {out=} {dipper_to_out=}"
                            # TODO: do I want to limit this to maximize room for dipped?
                            # If dipped will only go up, then 0 will leave lower space for dipped section.
                            y_choices = [0, 2, 4]
                    elif here in splits:
                        dipper_to_here = splits[here]
                        if dipper_to_here.y > here.y:  # dipper below
                            y_choices = [0]
                        elif dipper_to_here.y < here.y:  # dipper above
                            y_choices = [4]
                        else:  # dipper came from... behind!
                            assert in_desc.de is DE.elevator, f"{here=} {in_desc=}"
                            assert False, "I haven't implemented entering a split room from an elevator."
                            y_choices = [0 if out_through_in.y == 0 else 4]  # type: ignore[unreachable]
                    else:  # no split room involved
                        y_choices = [0, 2, 4]
                        if out not in dippers and here not in dippers:
                            # TODO: this could be opened up with dippers more if we're careful
                            if Corner.tr not in corners_used_in_this_room:
                                y_choices.append(1)
                            if Corner.br not in corners_used_in_this_room:
                                y_choices.append(3)
                    exit_x = 0xf0
                    exit_y = requires_y.get(here, requires_y.get(out, bm.random.choice(y_choices)))
                    out_desc = Desc(DE.door, exit_y, exit_x)
                    if here not in no_doors:
                        bm.door_manager.add_door(map_index, exit_y, exit_x, map_index)
                elif here.x > out.x:  # going to left
                    if out in splits:
                        dipper_to_out = splits[out]
                        if dipper_to_out.y > out.y:  # dipper below
                            y_choices = [0]
                        elif dipper_to_out.y < out.y:  # dipper above
                            y_choices = [4]
                        else:  # dipper coming from opposite side
                            assert dipper_to_out.x < out.x, f"{here=} {out=} {dipper_to_out=}"
                            y_choices = [0, 2, 4]
                    elif here in splits:
                        dipper_to_here = splits[here]
                        if dipper_to_here.y > here.y:  # dipper below
                            y_choices = [0]
                        elif dipper_to_here.y < here.y:  # dipper above
                            y_choices = [4]
                        else:  # dipper came from... behind!
                            assert in_desc.de is DE.elevator, f"{here=} {in_desc=}"
                            assert False, "I haven't implemented entering a split room from an elevator."
                            y_choices = [0 if out_through_in.y == 0 else 4]  # type: ignore[unreachable]
                    else:  # no split room involved
                        y_choices = [0, 2, 4]
                        if out not in dippers and here not in dippers:
                            if Corner.tl not in corners_used_in_this_room:
                                y_choices.append(1)
                            if Corner.bl not in corners_used_in_this_room:
                                y_choices.append(3)
                    exit_x = 0x08
                    exit_y = requires_y.get(here, requires_y.get(out, bm.random.choice(y_choices)))
                    out_desc = Desc(DE.door, exit_y, exit_x)
                    if here not in no_doors:
                        bm.door_manager.add_door(map_index, exit_y, exit_x, map_index)
                elif here.y < out.y:  # going down
                    if out in splits:
                        assert False, "haven't implemented entering split with elevator"
                        dipper_to_out = splits[out]  # type: ignore[unreachable]
                        if dipper_to_out.x > out.x:  # dipper right
                            assert Corner.bl not in corners_used_in_this_room, (
                                "logic for going in to dipper should have prevented this"
                            )
                            x_choices = [0x10]
                        elif dipper_to_out.x < out.x:  # dipper left
                            assert Corner.br not in corners_used_in_this_room, (
                                "logic for going in to dipper should have prevented this"
                            )
                            x_choices = [0xd0]
                        else:  # dipper coming from opposite side
                            assert dipper_to_out.y > out.y, f"{here=} {out=} {dipper_to_out=}"
                            x_choices = tuple(_safe_elevator_x)
                    elif here in splits:
                        dipper_to_here = splits[here]
                        if dipper_to_here.x > here.x:  # dipper right
                            x_choices = [0x10]
                        elif dipper_to_here.x < here.x:  # dipper left
                            x_choices = [0xd0]
                        else:  # dipper above
                            assert dipper_to_here.y < here.y
                            assert in_desc.de is DE.door
                            x_choices = [0x10 if out_through_in.x < 0x80 else 0xd0]
                    else:  # no split room, here or out
                        x_choices = [
                            x
                            for x in _safe_elevator_x
                            if ((x > 0x20 or Corner.bl not in corners_used_in_this_room) and
                                (x < 0xc0 or Corner.br not in corners_used_in_this_room))
                        ]
                    exit_x = bm.random.choice(x_choices)
                    # debug code
                    # if 0x10 in x_choices:
                    #     exit_x = 0x10
                    exit_y_5: Literal[5] = 5  # TODO: when mypy gets better literal narrowing, just use exit_y
                    out_desc = Desc(DE.elevator, exit_y_5, exit_x)
                    bm.door_manager.add_elevator(map_index, exit_y_5, exit_x, back_to_computer(here))
                elif here.y > out.y:  # going up
                    if out in splits:
                        assert False, "haven't implemented entering split with elevator"
                        dipper_to_out = splits[out]  # type: ignore[unreachable]
                        if dipper_to_out.x > out.x:  # dipper right
                            assert Corner.tl not in corners_used_in_this_room, (
                                "logic for going in to dipper should have prevented this"
                            )
                            x_choices = [0x10]
                        elif dipper_to_out.x < out.x:  # dipper left
                            assert Corner.tr not in corners_used_in_this_room, (
                                "logic for going in to dipper should have prevented this"
                            )
                            x_choices = [0xd0]
                        else:  # dipper coming from opposite side
                            assert dipper_to_out.y > out.y, f"{here=} {out=} {dipper_to_out=}"
                            x_choices = tuple(_safe_elevator_x)
                    elif here in splits:
                        dipper_to_here = splits[here]
                        if dipper_to_here.x > here.x:  # dipper right
                            x_choices = [0x10]
                        elif dipper_to_here.x < here.x:  # dipper left
                            x_choices = [0xd0]
                        else:  # dipper below
                            assert dipper_to_here.y > here.y
                            assert in_desc.de is DE.door
                            x_choices = [0x10 if out_through_in.x < 0x80 else 0xd0]
                    else:  # no split room, here or out
                        x_choices = [
                            x
                            for x in _safe_elevator_x
                            if ((x > 0x20 or Corner.tl not in corners_used_in_this_room) and
                                (x < 0xc0 or Corner.tr not in corners_used_in_this_room))
                        ]
                    exit_x = bm.random.choice(x_choices)
                    exit_y_0: Literal[0] = 0  # TODO: when mypy gets better literal narrowing, just use exit_y
                    out_desc = Desc(DE.elevator, exit_y_0, exit_x)
                    bm.door_manager.add_elevator(map_index, exit_y_0, exit_x, back_to_computer(here))
                else:
                    raise ValueError(f"equal? {here=} {out=}")

                edge_descriptions[here][out] = out_desc
                corners_used_in_this_room.extend(out_desc.corner_conflicts())
                parents[out] = here
            area_exit = _red_right_area_exits.get(map_index)
            if area_exit:
                bm.door_manager.add_door(map_index, area_exit.y, area_exit.x, map_index)
        q.extend(outs)

    for split, dipper in splits.items():
        split_row = bm.row_offset + split.y
        split_col = bm.col_offset + split.x
        split_map_index = split_row * 8 + split_col
        dipper_row = bm.row_offset + dipper.y
        dipper_col = bm.col_offset + dipper.x
        dipper_map_index = dipper_row * 8 + dipper_col

        split_edges = list(edge_descriptions[split].values())
        assert split_edges[0].de is DE.door, "didn't implement enter split through elevator"

        y_dipper: Literal[0, 5]
        y_split: Literal[0, 5]
        if dipper.y < split.y:  # dipper above
            y_dipper = 5
            y_split = 0
            x_not_allowed: Set[int] = set()
            for split_door in split_edges:
                if split_door.y < 2:
                    if split_door.x < 0x50:
                        x_not_allowed.update((0x00, 0x10, 0x20, 0x30, 0x40))
                    if split_door.x > 0x90:
                        x_not_allowed.update((0xa0, 0xb0, 0xc0, 0xd0, 0xe0, 0xf0))
            x_choices = [
                x
                for x in _safe_elevator_x
                if x not in x_not_allowed
            ]
            x = bm.random.choice(x_choices)
            dipper_desc = Desc(DE.elevator, y_dipper, x)
            split_desc = Desc(DE.elevator, y_split, x, True)
            bm.door_manager.add_elevator(dipper_map_index, y_dipper, x, back_to_computer(dipper))
            bm.door_manager.add_elevator(split_map_index, y_split, x, back_to_computer(dipper))
        elif dipper.y > split.y:  # dipper below
            y_dipper = 0
            y_split = 5
            x_not_allowed = set()
            for split_door in split_edges:
                if split_door.y > 2:
                    if split_door.x < 0x50:
                        x_not_allowed.update((0x00, 0x10, 0x20, 0x30, 0x40))
                    if split_door.x > 0x90:
                        x_not_allowed.update((0xa0, 0xb0, 0xc0, 0xd0, 0xe0, 0xf0))
            x_choices = [
                x
                for x in _safe_elevator_x
                if x not in x_not_allowed
            ]
            x = bm.random.choice(x_choices)
            dipper_desc = Desc(DE.elevator, y_dipper, x)
            split_desc = Desc(DE.elevator, y_split, x, True)
            bm.door_manager.add_elevator(dipper_map_index, y_dipper, x, back_to_computer(dipper))
            bm.door_manager.add_elevator(split_map_index, y_split, x, back_to_computer(dipper))
        elif dipper.x < split.x:  # dipper left
            x_dipper = 0xf0
            x_split = 0x08
            y_not_allowed: Set[int] = set()
            for split_door in split_edges:
                if split_door.x < 0x50:
                    if split_door.y < 2:
                        y_not_allowed.add(0)
                    if split_door.y > 2:
                        y_not_allowed.add(4)
            y_choices = [
                y
                for y in (0, 2, 4)
                if y not in y_not_allowed
            ]
            y = bm.random.choice(y_choices)
            dipper_desc = Desc(DE.door, y, x_dipper)
            split_desc = Desc(DE.door, y, x_split, True)
            if dipper not in no_doors:
                bm.door_manager.add_door(dipper_map_index, y, x_dipper, dipper_map_index)
        else:  # dipper right
            assert dipper.x > split.x
            x_dipper = 0x08
            x_split = 0xf0
            y_not_allowed = set()
            for split_door in split_edges:
                if split_door.x > 0x90:
                    if split_door.y < 2:
                        y_not_allowed.add(0)
                    if split_door.y > 2:
                        y_not_allowed.add(4)
            y_choices = [
                y
                for y in (0, 2, 4)
                if y not in y_not_allowed
            ]
            y = bm.random.choice(y_choices)
            dipper_desc = Desc(DE.door, y, x_dipper)
            split_desc = Desc(DE.door, y, x_split, True)
            if dipper not in no_doors:
                bm.door_manager.add_door(dipper_map_index, y, x_dipper, dipper_map_index)

        edge_descriptions[dipper][split] = dipper_desc
        edge_descriptions[split][dipper] = split_desc

    return edge_descriptions


def get_entrance_coords(here: Node, parent: Node, in_desc: Desc) -> Tuple[int, int]:
    """ y, x """
    if here.x < parent.x:  # came from right
        assert in_desc.de is DE.door and in_desc.x == 0x08, f"{here=}"
        entrance_x = 0xf0
        entrance_y = in_desc.y
    elif here.x > parent.x:  # came from left
        assert in_desc.de is DE.door and in_desc.x == 0xf0, f"{here=}"
        entrance_x = 0x08
        entrance_y = in_desc.y
    elif here.y < parent.y:  # came from below
        assert in_desc.de is DE.hallway_elevator or (in_desc.de is DE.elevator and in_desc.y == 0), f"{here=}"
        entrance_x = in_desc.x
        entrance_y = 5
    elif here.y > parent.y:  # came from above
        assert in_desc.de is DE.hallway_elevator or (in_desc.de is DE.elevator and in_desc.y == 5), f"{here=}"
        entrance_x = in_desc.x
        entrance_y = 0
    else:
        raise ValueError(f"equal? {here=} {parent=}")
    return entrance_y, entrance_x
