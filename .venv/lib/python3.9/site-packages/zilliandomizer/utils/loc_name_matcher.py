from dataclasses import dataclass
import time
from typing import Collection, Dict, Iterable, List, Tuple

from zilliandomizer.utils import parse_loc_name


@dataclass(frozen=True)
class LocCoords:
    name: str
    y: int
    x: int


_x_names = {
    0x00: "far left",
    0x30: "left",
    0x54: "left-center",
    0x78: "center",
    0x9c: "right-center",
    0xc0: "right",
    0xf0: "far right"
}

_x_list = list(_x_names.keys())


def all_locations_in_room() -> Iterable[str]:
    for v in ("top ", "mid ", "bottom "):
        for h in _x_names.values():
            yield v + h


def loc_name_maker(locs: Collection[str]) -> Dict[str, str]:
    """
    takes a collection of the location names of canisters in 1 room
    and returns a map of those names to descriptions of where in the room they are
    """
    top: List[LocCoords] = []
    tmd: List[LocCoords] = []
    mid: List[LocCoords] = []
    bmd: List[LocCoords] = []
    bot: List[LocCoords] = []

    for loc in locs:
        _, _, y, x = parse_loc_name(loc)
        this = LocCoords(loc, y, x)
        if this.y <= 0x18:
            top.append(this)
        elif this.y >= 0x98:
            bot.append(this)
        elif this.y == 0x58:
            mid.append(this)
        elif this.y < 0x58:
            tmd.append(this)
        else:  # y > 0x58
            bmd.append(this)

    if len(top) < len(mid):
        top.extend(tmd)
    else:  # top >= mid
        mid.extend(tmd)

    if len(mid) < len(bot):
        mid.extend(bmd)
    else:  # mid >= bot
        bot.extend(bmd)

    # now all of the locations are in top, mid, or bot

    top.sort(key=lambda lc: lc.x)
    mid.sort(key=lambda lc: lc.x)
    bot.sort(key=lambda lc: lc.x)

    def distance(lc: LocCoords, i: int) -> int:
        """ effective distance from `x` component of `lc` to `_x_list[i]` """
        d = abs(lc.x - _x_list[i])
        # a penalty for using the names that aren't as pretty
        if i in {2, 4}:
            d += 0x0b  # tunable magic number
        return d

    def shortest_pairs(lcs: List[LocCoords], from_index: int = 0) -> Tuple[List[int], int]:
        """ returns indexes to _x_list, and the total distance """
        if len(lcs) == 0:
            return [], 2000
        if len(lcs) == 1:
            lowest_d = distance(lcs[0], from_index)
            lowest_i = from_index
            for i in range(from_index + 1, len(_x_list)):
                here = distance(lcs[0], i)
                if here < lowest_d:
                    lowest_d = here
                    lowest_i = i
            return [lowest_i], lowest_d
        else:  # len > 1
            after = lcs[1:]
            lowest_l = []
            lowest_d = 2000
            for i in range(from_index, len(_x_list) - len(after)):
                after_l, after_d = shortest_pairs(after, i + 1)
                here_d = distance(lcs[0], i)
                total_d = here_d + after_d
                if total_d < lowest_d:
                    lowest_l = [i] + after_l
                    lowest_d = total_d
            return lowest_l, lowest_d

    top_i, _ = shortest_pairs(top)
    mid_i, _ = shortest_pairs(mid)
    bot_i, _ = shortest_pairs(bot)

    tr: Dict[str, str] = {}

    for y_name, lcs, xs in (
        ("top ", top, top_i),
        ("mid ", mid, mid_i),
        ("bottom ", bot, bot_i)
    ):
        for lc_i, x_i in enumerate(xs):
            tr[lcs[lc_i].name] = y_name + _x_names[_x_list[x_i]]

    return tr


def test() -> None:
    print(loc_name_maker([
        "r01c2y98xa0",
        "r01c2y98xb0",
        "r01c2y98xc0",
        "r01c2y98xd0",
    ]))

    print(loc_name_maker([
        "r01c2y98x70",
        "r01c2y98x80",
        "r01c2y98x90",
        "r01c2y98xa0",
    ]))

    print(loc_name_maker([
        "r01c2y18x70",
        "r01c2y98x80",
        "r01c2y98x90",
        "r01c2y98xa0",
    ]))

    print(loc_name_maker([
        "r01c2y18x70",
        "r01c2y78x80",
        "r01c2y98x90",
        "r01c2y98xa0",
    ]))

    # room r07c1
    print(loc_name_maker([
        "r07c1y18x10",
        "r07c1y58x30",
        "r07c1y58x40",
        "r07c1y18x50",
        "r07c1y18x90",
    ]))


if __name__ == "__main__":
    print_saved = print
    # print = lambda x: None
    start = time.time()
    for _ in range(1):
        test()
    stop = time.time()
    print_saved(stop - start)
