from collections import defaultdict
from typing import Dict, List, Mapping, Tuple, Union

from zilliandomizer.logic_components.regions import Region
from zilliandomizer.logic_components.locations import Location, Req
from zilliandomizer.map_gen.base import Base


class MapBuilder:
    r: Dict[str, Region]
    locations: Mapping[str, Location]
    reg_name_to_loc_name: Mapping[str, List[str]]

    def __init__(self, locations: Mapping[str, Location]) -> None:
        self.r = {}
        self.locations = locations

        self.reg_name_to_loc_name = defaultdict(list)
        for loc_name in locations.keys():
            split = loc_name.split('y')
            if len(split) == 2:
                reg_name = split[0]
                self.reg_name_to_loc_name[reg_name].append(loc_name)
                assert len(self.reg_name_to_loc_name[reg_name]) < 8, f"{reg_name=}"
            else:
                assert loc_name == "main", f"loc_name with no region: {loc_name}"

    @staticmethod
    def _region_name(row: int, col: int) -> Tuple[str, int]:
        """ `(name, map_index)` - example: `("r01c2", 10)` """
        assert (1 <= row <= 16) and (0 <= col <= 7), f"{row=} {col=}"
        return f"r{row:02}c{col}", row * 8 + col

    def _add_region(self, name: str, door_id: int, locs: List[str]) -> None:
        region = Region(name, door_id)
        self.r[name] = region
        assert len(locs) < 8, f"{name=} {locs=}"
        for loc_name in locs:
            region.locations.append(self.locations[loc_name])

    def room(self, row: int, col: int, expected_cans: int, door: bool) -> None:
        """
        normal room, not hallway, not split

        door if the doors in this room are opened by the computer in this room
        """
        name, map_index = self._region_name(row, col)
        door_id = map_index if door else 0
        assert len(self.reg_name_to_loc_name[name]) == expected_cans
        self._add_region(name, door_id, self.reg_name_to_loc_name[name])

    def hall(self, name: str) -> None:
        """ just a name, no canisters or computers """
        self._add_region(name, 0, [])

    def split(self, row: int, col: int, cans: Mapping[str, List[str]], door: bool) -> None:
        """
        ```
        cans = {
            region_name_suffix: [location_name, ...]
        }
        ```

        The section that has at least 4 canisters gets the door (if there's a door).
        """
        base_name, map_index = self._region_name(row, col)
        for ext, locs in cans.items():
            name = base_name + ext
            door_id = map_index if (door and len(locs) >= 4) else 0
            self._add_region(name, door_id, locs)


def make_blue(mb: MapBuilder) -> None:
    """ creates regions up to "between_blue_red" and connects everything up to the same """

    mb.hall("start")
    mb.hall("left_of_start")

    mb.room(2, 0, 5, False)
    mb.room(2, 7, 6, True)

    mb.room(1, 2, 5, True)
    mb.room(1, 3, 4, False)
    mb.room(1, 5, 6, False)  # there is a door, but treat as if no door
    mb.room(1, 7, 3, False)

    mb.room(3, 2, 5, True)
    mb.room(3, 3, 5, True)
    mb.room(3, 4, 5, True)
    mb.room(3, 5, 6, True)

    mb.room(4, 1, 6, True)
    mb.room(4, 2, 5, True)
    mb.room(4, 4, 6, True)
    mb.room(4, 5, 6, True)

    mb.hall("between_blue_red")

    # connections

    mb.r["start"].to(mb.r["r02c7"])
    mb.r["r02c7"].to(mb.r["r01c7"], door=True)

    mb.r["start"].to(mb.r["left_of_start"], union=(Req(skill=1), Req(hp=300)))
    mb.r["left_of_start"].to(mb.r["r02c0"])
    mb.r["left_of_start"].to(mb.r["r01c2"])
    mb.r["r01c2"].to(mb.r["r01c3"], door=True)
    mb.r["r01c3"].to(mb.r["r01c5"], union=(Req(skill=1), Req(hp=180)))

    mb.r["start"].to(mb.r["r03c5"])
    mb.r["r03c5"].to(mb.r["r03c4"], door=True)
    mb.r["r03c4"].connections[mb.r["r03c5"]].jump = 1
    mb.r["r03c4"].to(mb.r["r03c3"], door=True)
    mb.r["r03c3"].to(mb.r["r03c2"], door=True)

    mb.r["r03c2"].to(mb.r["r04c1"], door=True)
    mb.r["r04c1"].to(mb.r["r04c2"], door=True)
    mb.r["r03c2"].to(mb.r["r04c2"], door=True)

    mb.r["r04c2"].to(mb.r["r04c4"], door=True)
    mb.r["r04c4"].to(mb.r["r04c5"], door=True)

    mb.r["r04c5"].to(mb.r["between_blue_red"], door=True)


def make_red_right(mb: MapBuilder) -> None:
    """ given "between_blue_red" create and connect up to "red_elevator" """

    mb.room(5, 3, 5, True)
    mb.split(5, 4, {
        "sw": [
            "r05c4y18xb0",
            "r05c4y58x50",
            "r05c4y18xa0",
            "r05c4y58x30",
            "r05c4y98x80",
        ],
        "ne": [
            "r05c4y18xe0",
        ]
    }, True)
    mb.room(5, 5, 5, False)
    mb.room(5, 7, 6, True)

    mb.room(6, 3, 5, True)
    mb.room(6, 4, 5, True)
    mb.room(6, 6, 5, True)
    mb.room(6, 7, 5, True)

    mb.room(7, 3, 6, True)
    mb.room(7, 4, 2, False)
    mb.room(7, 5, 6, True)
    mb.room(7, 6, 6, True)
    mb.room(7, 7, 4, True)

    mb.room(8, 3, 6, True)
    mb.split(8, 4, {
        "ne": [
            "r08c4y18x40",
            "r08c4y98xa0",
            "r08c4y18x10",
            "r08c4y18xe0",
            "r08c4y58xe0",
        ],
        "sw": [  # red scope room
            "r08c4y98x30",
        ],
    }, True)
    mb.room(8, 5, 6, True)
    mb.room(8, 6, 6, True)
    mb.room(8, 7, 5, True)

    mb.room(9, 3, 5, True)
    mb.room(9, 4, 5, True)
    mb.room(9, 5, 5, True)
    mb.room(9, 7, 2, False)

    mb.hall("red_elevator")

    # connections

    mb.r["between_blue_red"].to(mb.r["r05c5"])
    mb.r["between_blue_red"].to(mb.r["r05c7"])

    mb.r["r05c7"].to(mb.r["r06c7"], door=True, union=(Req(skill=1), Req(hp=360)))
    mb.r["r06c7"].connections[mb.r["r05c7"]].hp = 120
    mb.r["r06c7"].to(mb.r["r06c6"], door=True)

    # r06c6 is red junction

    # left

    mb.r["r06c6"].to(mb.r["r06c4"], door=True)
    mb.r["r06c4"].to(mb.r["r06c3"], door=True)
    mb.r["r06c3"].to(mb.r["r05c3"], door=True)
    mb.r["r05c3"].to(mb.r["r05c4sw"], door=True)
    mb.r["r05c4sw"].to(mb.r["r05c4ne"], door=True, union=(Req(skill=1), Req(hp=300)))

    # down left

    mb.r["r06c6"].to(mb.r["r07c6"], door=True)
    mb.r["r07c6"].to(mb.r["r07c5"], door=True)
    mb.r["r07c5"].to(mb.r["r07c4"], door=True)
    mb.r["r07c4"].to(mb.r["r07c3"])
    mb.r["r07c3"].to(mb.r["r08c3"], door=True)
    mb.r["r08c3"].to(mb.r["r08c4sw"])

    # down right

    mb.r["r07c6"].to(mb.r["r07c7"], door=True)
    mb.r["r07c7"].to(mb.r["r08c7"], door=True)
    mb.r["r08c7"].to(mb.r["r08c6"], door=True)
    mb.r["r08c6"].to(mb.r["r08c5"], door=True)
    mb.r["r08c5"].to(mb.r["r08c4ne"], door=True)
    mb.r["r08c4ne"].to(mb.r["r09c4"], door=True)
    mb.r["r09c4"].to(mb.r["r09c5"], door=True)
    mb.r["r09c5"].to(mb.r["r09c7"], door=True)
    mb.r["r09c4"].to(mb.r["r09c3"], door=True)

    mb.r["r09c3"].to(mb.r["red_elevator"], door=True)
    mb.r["r08c3"].to(mb.r["red_elevator"], door=True)
    mb.r["r06c3"].to(mb.r["red_elevator"], door=True)


def make_red_left(mb: MapBuilder) -> None:
    """ given "red_elevator" create and connect up to "big_elevator" """

    mb.room(5, 1, 5, True)
    mb.room(6, 1, 5, True)
    mb.room(7, 1, 5, True)
    mb.room(9, 1, 3, False)
    mb.hall("big_elevator")

    # connections

    mb.r["red_elevator"].to(mb.r["r05c1"])
    mb.r["r05c1"].to(mb.r["r06c1"], door=True)
    mb.r["r06c1"].to(mb.r["r07c1"], door=True)
    mb.r["r07c1"].to(mb.r["r09c1"], door=True)

    mb.r["r07c1"].to(mb.r["big_elevator"], door=True)


def make_red(mb: MapBuilder, base: Union[Base, None]) -> None:
    """ given "between_blue_red" creates regions up to "big_elevator" and connects everything up to the same """

    if base:
        from zilliandomizer.map_gen.region_maker import make_red_right_bm
        make_red_right_bm(base.red, mb, {})
    else:  # vanilla
        make_red_right(mb)
    make_red_left(mb)


def make_paperclip(mb: MapBuilder, base: Union[Base, None]) -> None:
    """ from "big_elevator" to everything below red """

    if base:
        from zilliandomizer.map_gen.region_maker import make_paperclip_bm
        assert base.pudding_cans
        make_paperclip_bm(base.paperclip, mb, base.pc_splits, base.pudding_cans)
        return

    mb.split(10, 1, {
        "n": [
            "r10c1y78xa0",
            "r10c1y58x70",
            "r10c1y58x40",
        ],
        "s": [
            "r10c1y98x70",
        ],
    }, False)
    mb.room(10, 2, 6, True)
    mb.split(10, 3, {
        "s": [
            "r10c3y98x50",
            "r10c3y98x70",
            "r10c3y98x90",
            "r10c3y58xe0",
            "r10c3y58x10",
        ],
        "n": [
            "r10c3y18x20",
        ],
    }, True)
    mb.split(10, 4, {
        "e": [
            "r10c4y18xa0",
            "r10c4y98x80",
            "r10c4y78xb0",
            "r10c4y58x80",
        ],
        "w": [
            "r10c4y18x20",
            "r10c4y58x60",
        ]
    }, True)
    mb.room(10, 5, 1, False)  # main computer

    mb.split(11, 1, {
        "e": [
            "r11c1y98xc0",
            "r11c1y98xe0",
            "r11c1y98xd0",
        ],
        "w": [
            "r11c1y58x10",
            "r11c1y58x20",
        ],
    }, False)
    mb.room(11, 2, 6, True)
    mb.room(11, 3, 6, True)
    mb.room(11, 4, 6, True)
    mb.split(11, 5, {
        "w": [
            "r11c5y98x50",
            "r11c5y98x40",
            "r11c5y38x30",
            "r11c5y18x60",
        ],
        "e": [
            "r11c5y58x50",
            "r11c5y58x60",
        ],
    }, True)
    mb.split(11, 6, {
        "ne": [
            "r11c6y98xc0",
            "r11c6y18xb0",
            "r11c6y18x20",
            "r11c6y18x90",
        ],
        "sw": [
            "r11c6y98x50",
            "r11c6y98x30",
        ],
    }, True)

    mb.room(12, 1, 5, False)
    mb.room(12, 2, 5, True)
    mb.room(12, 3, 6, True)
    mb.room(12, 4, 6, True)
    mb.split(12, 5, {
        "s": [
            "r12c5y58xd0",
            "r12c5y98xd0",
            "r12c5y58xe0",
            "r12c5y98x10",
            "r12c5y58xc0",
            "r12c5y58x30",
        ],
        "n": [

        ],
    }, True)
    mb.split(12, 6, {
        "s": [
            "r12c6y58x20",
            "r12c6y98x20",
            "r12c6y58xa0",
            "r12c6y98xe0",
            "r12c6y98xb0",
        ],
        "n": [

        ],
    }, True)

    mb.split(13, 1, {
        "e": [
            "r13c1y58xa0",
            "r13c1y18x80",
            "r13c1y18x70",
            "r13c1y98xa0",
            "r13c1y58x90",
        ],
        "w": [
            "r13c1y98x10"
        ],
    }, True)
    mb.room(13, 2, 5, True)
    mb.split(13, 3, {
        "s": [
            "r13c3y58x30",
            "r13c3y58xc0",
            "r13c3y98xe0",
            "r13c3y58xd0",
            "r13c3y58xe0",
        ],
        "n": [

        ],
    }, True)
    mb.room(13, 4, 5, True)
    mb.split(13, 5, {
        "nw": [
            "r13c5y58x70",
            "r13c5y18x10",
            "r13c5y98x80",
            "r13c5y58x50",
            "r13c5y58x90",
        ],
        "se": [  # canister behind the door
            "r13c5y98xa0",
        ],
    }, True)
    mb.split(13, 6, {
        "w": [
            "r13c6y18x50",
            "r13c6y58x30",
            "r13c6y98xa0",
            "r13c6y18x40",
            "r13c6y58x20",
        ],
        "e": [
            "r13c6y18xe0",
        ],
    }, True)

    mb.split(14, 1, {
        "ne": [
            "r14c1y18x70",
            "r14c1y18x10",
            "r14c1y98xc0",
            "r14c1y18x40",
        ],
        "sw": [
            "r14c1y98x70",
            "r14c1y98x30",
        ],
    }, False)
    mb.room(14, 2, 5, True)
    mb.room(14, 3, 6, True)
    mb.room(14, 4, 5, True)
    mb.room(14, 5, 6, True)
    mb.split(14, 6, {
        "n": [
            "r14c6y18x10",
            "r14c6y18x30",
            "r14c6y58xd0",
            "r14c6y18x50",
            "r14c6y58xe0",
        ],
        "s": [
            "r14c6y98x10",
        ],
    }, True)

    mb.split(15, 2, {
        "nw": [
            "r15c2y18xc0",
            "r15c2y98x30",
            "r15c2y18x70",
            "r15c2y58xd0",
            "r15c2y58xb0",
        ],
        "se": [
            "r15c2y98x80",
        ],
    }, True)
    mb.split(15, 3, {
        "e": [
            "r15c3y58x70",
            "r15c3y18x50",
            "r15c3y18x80",
            "r15c3y18x70",
            "r15c3y18x60",
        ],
        "w": [
            "r15c3y58x10",
        ],
    }, True)
    mb.room(15, 4, 5, True)
    mb.room(15, 5, 5, True)
    mb.split(15, 6, {
        "w": [
            "r15c6y98x50",
            "r15c6y98x60",
            "r15c6y78x30",
            "r15c6y78x20",
            "r15c6y58x10",
        ],
        "e": [
            "r15c6y18xd0",
        ],
    }, True)

    mb.split(16, 2, {
        "e": [
            "r16c2y18x70",
            "r16c2y18x60",
            "r16c2y60x80",
            "r16c2y18x50",
            "r16c2y18x80",
        ],
        "w": [
            "r16c2y18x30",
        ],
    }, True)

    mb.hall("final_elevator")

    # connections

    mb.r["big_elevator"].to(mb.r["r11c1w"])
    mb.r["r11c1w"].to(mb.r["r10c1s"], door=mb.r["r11c2"].door)  # this is a strange door req, not a mistake
    mb.r["big_elevator"].to(mb.r["r13c1w"])
    mb.r["big_elevator"].to(mb.r["r14c1sw"], door=mb.r["r14c2"].door)  # a not-as-strange door req
    mb.r["big_elevator"].to(mb.r["r16c2w"])
    mb.r["big_elevator"].to(mb.r["r15c2nw"])

    # paperclip time

    mb.r["r15c2nw"].to(mb.r["r14c2"], door=True)
    mb.r["r14c2"].to(mb.r["r14c1ne"], door=True)
    mb.r["r14c1ne"].to(mb.r["r14c1sw"])  # fall within room
    mb.r["r14c1sw"].connections[mb.r["r14c1ne"]].jump = 5
    mb.r["r14c2"].to(mb.r["r14c3"], door=True)
    mb.r["r14c3"].to(mb.r["r13c3s"], door=True)
    mb.r["r14c3"].to(mb.r["r14c4"], door=True)
    mb.r["r14c4"].to(mb.r["r15c4"], door=True)
    mb.r["r15c4"].to(mb.r["r15c3e"], door=True)
    mb.r["r14c4"].to(mb.r["r13c4"], door=True)

    # long path paperclip junction

    # right

    mb.r["r13c4"].to(mb.r["r13c5nw"], door=True)
    mb.r["r13c5nw"].to(mb.r["r12c5s"], door=True)
    mb.r["r12c5s"].to(mb.r["r12c6s"], door=True)
    mb.r["r13c5nw"].to(mb.r["r13c5se"], door=True)
    mb.r["r13c5se"].to(mb.r["r14c5"], door=mb.r["r13c5nw"].door)  # that's when this elevator appears
    mb.r["r14c5"].to(mb.r["r15c5"], door=True)
    mb.r["r15c5"].connections[mb.r["r14c5"]].jump = 3
    mb.r["r15c5"].to(mb.r["r15c6w"], door=True, jump=3)
    # TODO: this r15c5 to r15c6w jump 3 is not required,
    # it's a workaround for reverse requirements (r15c5 to r14c5)
    # not being taken into account by the logic
    mb.r["r13c5se"].to(mb.r["r13c6w"])
    mb.r["r13c6w"].to(mb.r["r14c6n"], door=True)
    mb.r["r13c6e"].to(mb.r["r13c6w"])  # fall from red card
    mb.r["r13c6w"].connections[mb.r["r13c6e"]].jump = 5

    # left

    mb.r["r13c4"].to(mb.r["r13c3n"], door=True)
    mb.r["r13c3n"].to(mb.r["r13c2"], door=mb.r["r13c3s"].door)  # pre-opened door
    mb.r["r13c2"].to(mb.r["r13c1e"], door=True)
    mb.r["r13c1e"].to(mb.r["r12c1"], door=True)
    mb.r["r13c2"].to(mb.r["r12c2"], door=True, jump=3)
    mb.r["r12c2"].to(mb.r["r12c3"], door=True)
    mb.r["r12c3"].to(mb.r["r11c3"], door=True)
    mb.r["r11c3"].to(mb.r["r11c4"], door=True)
    mb.r["r11c4"].to(mb.r["r11c5w"], door=True)
    mb.r["r11c4"].to(mb.r["r10c4e"], door=True)
    mb.r["r11c3"].to(mb.r["r11c2"], door=True)
    mb.r["r11c2"].to(mb.r["r11c1e"], door=True)
    mb.r["r11c2"].to(mb.r["r10c2"], door=True)
    mb.r["r10c2"].to(mb.r["r10c1n"], door=True)
    mb.r["r10c2"].to(mb.r["r10c3s"], door=True)
    mb.r["r10c3s"].to(mb.r["r10c4w"], door=True)
    mb.r["r10c4w"].to(mb.r["r10c3n"], door=mb.r["r10c4e"].door)  # floppy  # pre-opened door

    # backtrack for Champ

    mb.r["r12c3"].to(mb.r["r12c4"], door=True)
    mb.r["r12c4"].connections[mb.r["r12c3"]].union = (Req(skill=1), Req(jump=5))  # not easy to get out of there
    mb.r["r12c4"].to(mb.r["r12c5n"], door=True, jump=2)
    mb.r["r12c5n"].to(mb.r["r12c6n"], door=mb.r["r12c5s"].door)  # pre-opened door
    mb.r["r12c6n"].to(mb.r["r11c6ne"], door=mb.r["r12c6s"].door)  # pre-opened door
    mb.r["r11c6ne"].to(mb.r["r11c5e"], door=True, jump=3)  # Champ - jump req here because exit logic doesn't work
    mb.r["r11c5e"].connections[mb.r["r11c6ne"]].jump = 3  # This is why Champ couldn't get out.
    mb.r["r11c5e"].connections[mb.r["r11c6ne"]].skill = 2  # hard jump - TODO: find out if this requires speed
    # TODO: or jump 5 to get out
    mb.r["r11c5e"].to(mb.r["r11c6sw"], door=mb.r["r11c5w"].door)  # pre-opened door

    # go mode!

    mb.r["r14c3"].to(mb.r["r15c3w"], door=True)
    mb.r["r15c3w"].to(mb.r["r15c2se"], door=mb.r["r15c3e"].door)  # pre-opened door
    mb.r["r15c2se"].to(mb.r["r16c2e"], door=mb.r["r15c2nw"].door)
    mb.r["r16c2e"].to(mb.r["r15c6e"], door=True)  # long hallway
    mb.r["r15c6e"].to(mb.r["r14c6s"], door=mb.r["r15c6w"].door)  # pre-opened door
    # dun, dun, du-u-un-n-n-n....
    mb.r["r14c6s"].to(mb.r["final_elevator"], door=mb.r["r14c6n"].door)  # pre-opened door
    mb.r["final_elevator"].to(mb.r["r13c6e"])  # pick up red id card
    mb.r["final_elevator"].to(mb.r["r10c5"])  # main computer


def make_regions(locations: Mapping[str, Location], base: Union[Base, None] = None) -> Dict[str, Region]:
    """ return { region_name: region } """
    mb = MapBuilder(locations)

    make_blue(mb)
    make_red(mb, base)
    make_paperclip(mb, base)

    return mb.r
