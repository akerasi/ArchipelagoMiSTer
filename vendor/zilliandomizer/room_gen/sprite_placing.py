from dataclasses import dataclass
from random import shuffle
from typing import Container, Dict, FrozenSet, List, Literal
from zilliandomizer.room_gen.common import Coord
from zilliandomizer.room_gen.maze import BOTTOM, LEFT, RIGHT, TOP, Cell, Grid, MakeFailure


class AutoGunPlaces:
    down: List[Coord]
    right: List[Coord]
    left: List[Coord]

    def __init__(self) -> None:
        self.down = []
        self.right = []
        self.left = []


def auto_gun_places(g: Grid, exits: Container[Coord]) -> AutoGunPlaces:
    """
    finds all the places that auto-guns can go in each orientations
    and shuffles them within each orientation
    """
    tr = AutoGunPlaces()
    for y, row in enumerate(g.data):
        for x, this_cell in enumerate(row):
            if this_cell != Cell.wall and not g.in_exit(y, x, exits):
                here = (y, x)
                if y == TOP or g.data[y - 1][x] != Cell.space:
                    tr.down.append(here)
                if x == LEFT or g.data[y][x - 1] == Cell.wall:
                    tr.right.append(here)
                if x == RIGHT or g.data[y][x + 1] == Cell.wall:
                    tr.left.append(here)
    shuffle(tr.down)
    shuffle(tr.right)
    shuffle(tr.left)
    return tr


@dataclass
class BarPlace:
    """
    horizontal bars go at the bottom of the large tiles
    """
    c: Coord
    horizontal: bool
    length: int


class BarPlaces:
    floor_things: FrozenSet[Coord]
    bars: List[BarPlace]
    """
    horizontal bars go at the bottom of the large tiles
    (top of the tiles below for alarms)
    """

    def __init__(self, floor_things: FrozenSet[Coord]) -> None:
        self.floor_things = floor_things
        self.bars = []

    def add(self, c: Coord, horizontal: bool, length: int) -> None:
        """
        add a bar if it doesn't cross a sprite placed on the floor
        """
        if horizontal:
            for x in range(c[1], c[1] + length):
                here = (c[0], x)
                below = (c[0] + 1, x)
                if below in self.floor_things or here in self.floor_things:
                    return
        else:  # vertical
            for y in range(c[0], c[0] + length):
                here = (y, c[1])
                if here in self.floor_things:
                    return
        self.bars.append(BarPlace(c, horizontal, length))


def barrier_places(g: Grid, floor_things: List[Coord], exits: Container[Coord]) -> BarPlaces:
    tr = BarPlaces(frozenset(floor_things))
    for y, row in enumerate(g.data):
        for x, this_cell in enumerate(row):
            here = (y, x)
            if this_cell == Cell.space and not g.in_exit(y, x, exits):
                if x == LEFT or g.data[y][x - 1] != Cell.space:
                    # (the bottom of this) is a place where a horizontal bar can start
                    if x == RIGHT or g.data[y][x + 1] != Cell.space:
                        tr.add(here, True, 1)
                    else:  # space to the right
                        if not g.in_exit(y, x + 1, exits):
                            if x + 1 == RIGHT or g.data[y][x + 2] != Cell.space:
                                tr.add(here, True, 2)
                            # else would have to be longer than 2, but barrier max length is 2
                        # else moved into an exit
                if (
                    (y == TOP or g.data[y - 1][x] != Cell.space) and
                    (y < BOTTOM and g.data[y + 1][x] == Cell.floor)
                ):
                    # length 2 vertical bar can be here
                    tr.add(here, False, 2)
            elif this_cell == Cell.floor and not g.in_exit(y, x, exits) and (
                y > TOP and g.data[y - 1][x] != Cell.space
            ):
                # length 1 vertical bar can be here
                tr.add(here, False, 1)
    shuffle(tr.bars)

    # put the places I can't go first in the list, so they're the last to get chosen
    cant_go: List[BarPlace] = []
    can_go: List[BarPlace] = []
    goables = g.get_goables(3)
    for bar in tr.bars:
        y, x = bar.c
        if bar.horizontal:
            while y < BOTTOM and g.data[y][x] != Cell.floor:
                y += 1
        else:  # vertical
            y += bar.length - 1
        if (y, x, False) in goables:
            can_go.append(bar)
        else:
            cant_go.append(bar)
    tr.bars = cant_go + can_go
    return tr


def alarm_places(g: Grid, floor_things: List[Coord]) -> BarPlaces:
    """ returns places where alarms can go """
    tr = BarPlaces(frozenset(floor_things))
    for y, row in enumerate(g.data):
        for x, this_cell in enumerate(row):
            here = (y, x)
            # can horizontal start below this?
            if (
                (this_cell == Cell.space and not g.in_exit(y, x)) and
                (x == LEFT or g.data[y][x - 1] != Cell.space) and
                (not g.is_walkway[y + 1][x])
            ):
                # (below this) is a place where a horizontal bar can start
                end_x = x
                ran_into_exit_or_walkway = False
                while end_x <= RIGHT:
                    ran_into_exit_or_walkway = (
                        g.in_exit(y, end_x) or
                        bool(g.is_walkway[y + 1][end_x])
                    )
                    if g.data[y][end_x] != Cell.space or ran_into_exit_or_walkway:
                        break
                    end_x += 1
                if not ran_into_exit_or_walkway:
                    length = end_x - x
                    tr.add(here, True, length)
                # else ran into exit
            # can a vertical bar start here?
            if (
                (this_cell == Cell.space or this_cell == Cell.floor) and
                (not g.is_walkway[y][x]) and
                (not g.in_exit(y, x)) and
                (x > LEFT and g.data[y][x - 1] != Cell.wall) and
                (
                    y == TOP or
                    g.data[y - 1][x - 1] != Cell.space or
                    g.data[y - 1][x] != Cell.space
                )
            ):
                end_y = y
                ran_into_exit_or_walkway = False
                while end_y <= BOTTOM:
                    ran_into_exit_or_walkway = (
                        g.in_exit(end_y, x) or
                        bool(g.is_walkway[end_y][x])
                    )
                    if (
                        g.data[end_y][x] == Cell.floor or
                        g.data[end_y][x - 1] == Cell.floor or
                        ran_into_exit_or_walkway
                    ):
                        break
                    end_y += 1
                if not ran_into_exit_or_walkway:
                    length = end_y + 1 - y
                    # red vertical alarms can only be
                    # length 2, ceiling to floor, starting in even row
                    if 0x28 <= g.map_index < 0x50:
                        if (
                            (length == 2) and
                            (y & 1 == 0) and
                            (y == TOP or g.data[y - 1][x] != Cell.space) and
                            (g.data[end_y][x] == Cell.floor and not g.is_walkway[end_y][x])
                        ):
                            tr.add(here, False, length)
                        # else can't go here in red
                    else:  # not red
                        # length 1 vertical can't be between floor and ceiling
                        if length == 1:
                            if y == TOP or g.data[y - 1][x] != Cell.space:
                                if this_cell != Cell.floor:
                                    tr.add(here, False, length)
                                # else ceiling to floor in length 1
                            else:  # space above
                                tr.add(here, False, length)
                        elif length < 5:  # long verticals take up too much memory
                            tr.add(here, False, length)
                # else ran into exit with vertical
            # else can't start vertical here
        # end for x in row
    # end for y in grid
    shuffle(tr.bars)

    # put the places I can't go first in the list, so they're the last to get chosen
    cant_go: List[BarPlace] = []
    can_go: List[BarPlace] = []
    goables = g.get_goables(3)
    for bar in tr.bars:
        y, x = bar.c
        if bar.horizontal:
            while y < BOTTOM and g.data[y][x] != Cell.floor:
                y += 1
            if (y, x, False) in goables:
                can_go.append(bar)
            else:
                cant_go.append(bar)
        else:  # vertical
            y += bar.length - 1
            if (y, x, False) in goables or (y, x - 1, False) in goables:
                can_go.append(bar)
            else:
                cant_go.append(bar)
    tr.bars = cant_go + can_go
    return tr


def choose_alarms(ap: BarPlaces, count: int) -> Dict[int, Literal["v", "h", "n"]]:
    """ returns input to `Alarms.add_alarms_to_room_terrain_bytes` """

    def collides(a: BarPlace, b: BarPlace) -> bool:
        if a.horizontal == b.horizontal:
            return False
        if a.horizontal:
            a, b = b, a
        # a vertical, b horizontal
        a_range = range(a.c[0], a.c[0] + a.length)
        if (b.c[0] + 1) not in a_range:
            return False
        b_range = range(b.c[1], b.c[1] + b.length)
        return a.c[1] in b_range

    tr: Dict[int, Literal["v", "h", "n"]] = {}
    while count > 0:
        if len(ap.bars) == 0:
            # print("warning: not enough places to put alarms")
            if len(tr) < 1:
                raise MakeFailure("zero places to put alarms in alarm room")
            break
        this_one = ap.bars.pop()
        count -= 1

        # remove everything that collides with this one
        remaining_bars: List[BarPlace] = []
        for bar in ap.bars:
            if not collides(this_one, bar):
                remaining_bars.append(bar)
        ap.bars = remaining_bars

        # add modifications
        if this_one.horizontal:
            y = this_one.c[0] + 1  # + 1 because horizontal alarms at bottom of tile
            # x + 1 for left wall
            for x in range(this_one.c[1] + 1, this_one.c[1] + this_one.length + 1):
                index = y * 16 + x
                tr[index] = 'h'
        else:  # vertical
            x = this_one.c[1] + 1  # + 1 for left wall
            for y in range(this_one.c[0], this_one.c[0] + this_one.length):
                index = y * 16 + x
                tr[index] = 'v'

    return tr
