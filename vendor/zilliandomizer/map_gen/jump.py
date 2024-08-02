from random import choice, random
from typing import Dict

MAX_JUMP = 3


def room_jump_requirements() -> Dict[int, int]:
    """ returns map of room index to the jump requirement cap [1, 2, or 3] for that room """
    tr: Dict[int, int] = {}  # room index to jump requirement

    progression_path = [29, 28, 27, 26, 34, 36, 37, 47, 55, 54]  # down from 6666 until junction in red

    # tunable magic number
    extra_2 = 5  # inverse probability for jump requirements left and right of 6666
    # if progression path down is blocked early by jump,
    # there will be a higher chance of not blocking by jump left and right

    current_jump_ability = 1

    # tunable magic number
    escalation_chance = 0.25  # prob of blocking the current jump in each room

    for room in progression_path:
        if room == 36 and current_jump_ability < 2:
            # room 36 is one of the best chances for jump 2 requirement,
            # so force ability for chance at requirement
            current_jump_ability = 2
        elif (
            random() < (escalation_chance if current_jump_ability == 1 else escalation_chance * 0.25) and
            current_jump_ability < MAX_JUMP
        ):
            current_jump_ability += 1
        tr[room] = current_jump_ability
        if current_jump_ability == 1:
            extra_2 -= 1  # tunable magic number
    lr_chances = [2, 3]
    for _ in range(extra_2):
        lr_chances.append(2)
    tr[10] = choice(lr_chances)
    tr[11] = tr[10]  # TODO: progressive escalation here too?
    tr[13] = tr[10]
    tr[23] = choice(lr_chances)
    tr[15] = tr[23]
    tr[16] = choice(lr_chances)

    # from red junction
    red_progressions = [
        [52, 51],
        [62, 61, 60, 59, 67],
        [62, 63, 71, 70, 69, 68, 76, 75]
    ]
    continued = [41, 49, 57, 122, 114]

    progression_path = choice(red_progressions) + continued
    for room in progression_path:
        if (
            random() < escalation_chance and
            current_jump_ability < MAX_JUMP
        ):
            current_jump_ability += 1
        tr[room] = current_jump_ability

    all_rooms = [
        10, 11, 13, 15,
        16, 23,
        26, 27, 28, 29,
        33, 34, 36, 37,
        41, 43, 44, 45, 47,
        49, 51, 52, 54, 55,
        57, 59, 60, 61, 62, 63,
        65, 67, 68, 69, 70, 71,
        73, 75, 76, 77, 79,
        81, 82, 83, 84, 85, 86,
        89, 90, 91, 92, 93, 94,
        97, 98, 99, 100, 101, 102,
        105, 106, 107, 108, 109, 110,
        113, 114, 115, 116, 117, 118,
        122, 123, 124, 125, 126,
        130
    ]

    # everything not already assigned gets jump 3 ability
    for room in all_rooms:
        if room not in tr:
            tr[room] = 3

    return tr


def test() -> None:
    reqs = room_jump_requirements()
    for map_index in range(17*8):
        if map_index in reqs:
            print(f"{reqs[map_index]} ", end="")
        else:
            print("- ", end="")
        if map_index % 8 == 7:
            print()


if __name__ == "__main__":
    test()
