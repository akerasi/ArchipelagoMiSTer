from typing import Any, Dict, Container, Iterable, Tuple
from collections import defaultdict

from zilliandomizer.options import ItemCounts, Options, error, ID, char_to_jump, \
    VBLR_CHOICES, chars, item_counts_factory
from zilliandomizer.options.random_gen import choices


def validate(op: Options) -> None:
    # TODO: when hp option is implemented, verify it with skill

    if sum(op.item_counts.values()) > 144:
        error("invalid item_counts - The maximumm total is 144.")

    opa_count = op.item_counts[ID.opa]
    max_from_opas = 1 + opa_count // op.opas_per_level
    max_level = op.max_level
    max_level_source = f"max_level ({op.max_level})"
    if max_from_opas < max_level:
        max_level = max_from_opas
        max_level_source = f"item_counts: opa ({opa_count}) / opas_per_level ({op.opas_per_level})"
    if char_to_jump["Apple"][op.jump_levels][max_level - 1] < 3:
        error("jump 3 not available - invalid combination of "
              f"jump_levels ({op.jump_levels}) and {max_level_source}")

    if op.floppy_req > op.item_counts[ID.floppy]:
        error(f"floppy_req {op.floppy_req} > item_counts: floppy {op.item_counts[ID.floppy]}")

    if (op.skill == 0 and op.max_level < 8) or (op.skill == 1 and op.max_level < 3):
        # because of hp requirement on final boss
        error(f"not allowed to lower max level to {op.max_level} with skill {op.skill}")


valid_choices: Dict[str, Container[Any]] = {
    "jump_levels": VBLR_CHOICES,
    "gun_levels": VBLR_CHOICES,
    "opas_per_level": range(1, 127),
    "max_level": range(1, 9),
    "tutorial": (True, False),
    "skill": range(6),
    "start_char": chars,
    "floppy_req": range(127),
    "continues": range(-1, 127),
    "randomize_alarms": (True, False),
    "early_scope": (True, False),
    "balance_defense": (True, False),
    "starting_cards": range(127),
    "map_gen": ("none", "rooms", "full"),
}

sub_options = {
    "item_counts": {
        "card": ID.card,
        "bread": ID.bread,
        "opa": ID.opa,
        "gun": ID.gun,
        "floppy": ID.floppy,
        "scope": ID.scope,
        "red": ID.red
    }
}


def make_empty_item_counts() -> ItemCounts:
    tr = item_counts_factory()
    for key in tr:
        tr[key] = 0
    return tr


# order:
# Some things that can be random need to go at the end (after item_counts).
# It's important that the sort is stable so that the sub-options stay together.
SORT_INDEX: Dict[str, int] = defaultdict(int, {
    "jump_levels": 1,     # depends on item_counts (assume 1 opas_per_level)
    "max_level": 2,       # depends on jump_levels (bot high enough to give jump 3)
    "opas_per_level": 3,  # depends on max_level (top low enough to give at least max_level)
    "gun_levels": 1,      # depends on item_counts
    "floppy_req": 1       # depends on item_counts
})


def cleaned_and_ordered(text: str) -> Iterable[Tuple[str, str]]:
    """ returns option, value """
    def _clean(line: str) -> str:
        try:
            line = line[:line.index("#")]
        except ValueError:
            pass  # no "#"

        return line.strip()

    def _filter(line: str) -> bool:
        return bool(len(line))

    def _format(line: str) -> Tuple[str, str]:
        split = line.split(":")
        if len(split) != 2:
            error(f'invalid line in options: "{line}"')
        option = split[0].strip().strip('"')
        value = split[1].strip().strip('"')
        return option, value

    def _ordered(line: Tuple[str, str]) -> int:
        return SORT_INDEX[line[0]]

    lines = sorted(map(_format, filter(_filter, map(_clean, text.split("\n")))),
                   key=_ordered)
    return lines


def parse_options(t: str) -> Options:
    # mypy doesn't know about __dataclass_fields__
    fields = Options.__dataclass_fields__

    def get_typed_value(option: str, value: str, opts: Options) -> Any:
        if value == "random" and option in choices:
            return choices[option](opts)

        typed_value: Any = value
        if option == "continues" and value == "infinity":
            typed_value = -1
        elif fields[option].type is bool:
            typed_value = (value.lower() in ("true", "yes", "on"))
        else:
            try:
                v = fields[option].type(value)
                typed_value = v
            except TypeError:
                # probably type Literal
                pass
        if typed_value not in valid_choices[option]:
            error(f"invalid value {value} for {option}")
        return typed_value

    tr = Options()
    parent_option = ""
    for option, value in cleaned_and_ordered(t):
        if option in fields and option not in sub_options:
            parent_option = ""
            typed_value = get_typed_value(option, value, tr)
            tr.__setattr__(option, typed_value)
        elif option in sub_options:
            parent_option = option
            tr.__setattr__(option, make_empty_item_counts())  # 0 for any item_counts not specified
        else:
            if parent_option == "":
                error(f"invalid option: {option}")
            if option not in sub_options[parent_option]:
                error(f"invalid sub-option {option} for option {parent_option}")

            # right now, the only suboption is item_counts
            try:
                int_value = int(value)
            except ValueError:
                error(f"invalid value {value} for sub-option {option} under {parent_option}")
            tr.__getattribute__(parent_option)[sub_options[parent_option][option]] = int_value

    validate(tr)
    return tr
