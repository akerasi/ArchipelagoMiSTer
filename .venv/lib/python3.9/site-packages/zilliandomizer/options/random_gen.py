from typing import Any, Callable, Dict, List
from random import choice, randrange

from zilliandomizer.options import Chars, chars, Options, VBLR, ID, \
    VBLR_CHOICES, char_to_jump, char_to_gun


def random_jump_levels(opts: Options) -> VBLR:
    opa_count = min(7, opts.item_counts[ID.opa])  # assuming 1 opas_per_level - That will be checked later.
    possible: List[VBLR] = [
        vblr for vblr in VBLR_CHOICES
        if char_to_jump["Apple"][vblr][opa_count] >= 3
    ]
    assert len(possible) > 0, "sanity check, jump Apple vanilla 0 == 3"
    return choice(possible)


def random_gun_levels(opts: Options) -> VBLR:
    gun_count = opts.item_counts[ID.gun]
    possible: List[VBLR] = [
        vblr for vblr in VBLR_CHOICES
        if (gun_count >= len(char_to_gun["Champ"][vblr])
            or char_to_gun["Champ"][vblr][gun_count] >= 3)
    ]
    assert len(possible) > 0, "sanity check, gun Champ vanilla 0 == 3"
    return choice(possible)


def random_floppy_req(opts: Options) -> int:
    # can require from 0 to all of the floppies
    return randrange(opts.item_counts[ID.floppy] + 1)


def random_max_level(opts: Options) -> int:
    # level of first jump 3 up to 8
    range_begin = char_to_jump["Apple"][opts.jump_levels].index(3) + 1
    return randrange(range_begin, 9)


def random_opas_per_level(opts: Options) -> int:
    opa_count = opts.item_counts[ID.opa]
    highest = max(1, opa_count // opts.max_level)
    return randrange(1, highest + 1)


def random_skill(opts: Options) -> int:
    return randrange(0, 6)


def random_start_char(opts: Options) -> Chars:
    return choice(chars)


# TODO: TypedDict
choices: Dict[str, Callable[[Options], Any]] = {
    "jump_levels": random_jump_levels,
    "gun_levels": random_gun_levels,
    "opas_per_level": random_opas_per_level,
    "max_level": random_max_level,
    "skill": random_skill,
    "start_char": random_start_char,
    "floppy_req": random_floppy_req,
}
""" Options field that can be chosen randomly: function for choosing randomly """
