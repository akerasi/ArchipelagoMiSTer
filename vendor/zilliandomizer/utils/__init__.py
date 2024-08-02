import math
from typing import NamedTuple, Optional, Tuple, Union, overload

from zilliandomizer.logic_components.items import RESCUE

"""
some rom data documentation:

room item data structure:
    first byte is number of items (canisters and rescues) in the room

    then that many copies of ItemData structure

    then after the list of items is complete:
        either 1 byte 0xff for no computer
        or 2 bytes to tell the location of the computer:
            00000vvv vvhhhhh0
            little endian (vvhhhhh0 first)

            vvvvv and hhhhh are counting small tiles

            vvvvv is vertical position (1-19)
                (0 puts a hole in the ceiling, 20 puts a hole in the floor)
                canister position 0x18 = computer position 00011
                                  0x38 = 00111
                                  0x58 = 01011
                                  0x78 = 01111
                                  0x98 = 10011
            hhhhh is horizontal position (2-28)
                (0, 1, 29, 30 put holes in the walls)
"""


class ItemData(NamedTuple):
    """
    item data structure

    1 byte for each of these values C Y X R M I S G
    """
    code: int
    """
    codes for type of data in item data (index 0):
    - 0A keyword
    - 26 normal item
    - 2A rescue (Apple/Champ)
    - 0D door to main computer
    - 2B hallway to shoot open
    - 2E unknown in final boss room  $2E $78 $90    $00 $00 $00 $00 $1B
    - 3D unknown in final boss room  $3D $08 $F8/08 $00 $00 $00 $00 $00
    """
    y: int
    """
    Y coordinate of canister in room (normal canister levels are 18, 38, 58, 78, 98)

    Apple is at 10, Champ is at 50 (because sprite is 8 pixels taller?)
    """
    x: int
    """
    X coordinate of canister in room

    (10 - E0 normally - main computer door is 18)
    """
    room_code: int
    """
    room code

    different even number for each room that has canisters - 94 is hallways that can be shot open
    """
    mask: int
    """
    mask for this item (keep track of open/got - ascending in this array (rescues use one also))
    """
    item_id: int
    """
    - 00-03 keywords
    - 04 empty
    - 05 card
    - 06 red card
    - 07 floppy
    - 08 bread
    - 09 opo
    - 0A gun
    - 0B scope
    - 0C something glitched (do I need any custom items? ;)
    ---
    - 00 Apple
    - 01 Champ

    (this item ID with the 2A code (1st byte of data structure) determines which char is rescued)
    (sprite doesn't matter, Y coord can be the extra 8 pixels up or not)
    ---
    - 00 main computer and stuff in final boss room
    """
    sprite: int
    """
    - 02 blue area gun1 canister
    - 04 blue area gun2 canister
    - 06 blue area gun3 canister
    - 08 red gun1 canister
    - 0A red gun2 canister
    - 0C red gun3 canister
    - 0E paperclip gun1
    - 10 paperclip gun2
    - 12 paperclip gun3
    - 14 Apple
    - 16 Champ

    LSB is set to display it already opened (only display, canister is still closed - opening it increments the image)
    """
    gun: int
    """
    gun required to open (0, 1, 2)  TODO: confirm (0, 1, 2)

    (Apple 01, Champ 00 - I don't know that this value is used for rescues.)
    """


def make_reg_name(map_index: int) -> str:
    """ without divisions """
    row = map_index // 8
    return f"r{row if row > 9 else ('0' + str(row))}c{map_index % 8}"


@overload
def make_loc_name(map_index: int, item_or_y: int, x: int) -> str: ...
@overload
def make_loc_name(map_index: int, item_or_y: ItemData) -> str: ...


def make_loc_name(map_index: int, item_or_y: Union[ItemData, int], x: Optional[int] = None) -> str:
    if isinstance(item_or_y, int):
        assert not (x is None)
        y = item_or_y
    else:
        # adjust height of rescues so they match with other items
        y = item_or_y.y + 8 if item_or_y.code == RESCUE else item_or_y.y
        x = item_or_y.x

    name = f"{make_reg_name(map_index)}y{hex(y)[-2:]}x{hex(x)[-2:]}"
    return name


def make_room_name(row: int, col: int) -> str:
    """ pretty "B-7" style """
    return f"{chr(ord('A') + row - 1)}-{col + 1}"


def parse_reg_name(name: str) -> Tuple[int, int]:
    """ row and col from region name """
    assert name[0] == 'r' and name[3] == 'c', name
    row = int(name[1:3])
    col = int(name[4])
    return row, col


def parse_loc_name(name: str) -> Tuple[int, int, int, int]:
    """ return row, col, y, x """
    room_str, coord_str = name.split('y')
    y_str, x_str = coord_str.split('x')
    row, col = parse_reg_name(room_str)
    y = int(y_str, 16)
    x = int(x_str, 16)
    return row, col, y, x


_interpolation_table = []


def _success_until_failure(k: float) -> float:
    """
    https://math.stackexchange.com/questions/4494669/roll-until-lose-game-with-changing-probability/4494686#4494686
    """
    prev_total = -1.0
    total = 0.0
    n = 0
    while total != prev_total:
        prev_total = total
        total += math.pow(k, (n * (n+1)) // 2)
        n += 1
    # print(f"n limit: {n}")  # never more than 48
    return total


def _search_with_e(e: float) -> float:
    """ return the k that produces e """
    bot = 0.0
    top = 1.0
    prev_guess = -1.0
    while top > bot:
        guess = (bot + top) / 2
        if guess == prev_guess:
            return guess
        prev_guess = guess
        result = _success_until_failure(guess)
        if result < e:
            bot = guess
        elif result > e:
            top = guess
        else:
            return guess
    return prev_guess


_interpolation_table = [
    _search_with_e(i / 4)
    for i in range(0)  # 128)
]
# TODO: move this to a different module so it's not taking up as much memory if I'm not using it
_interpolation_table = [
    0.0, 0.0, 0.0, 0.0, 1.1102230246251565e-16, 0.23658231162407528,
    0.42015503480061134, 0.5514488229227874, 0.6452227032360209,
    0.7134764693347571, 0.7642985416550656, 0.8029837489606948,
    0.8330271225884514, 0.8567802884384075, 0.8758603870722164,
    0.8914036917928823, 0.9042249439933254, 0.91491935245767,
    0.9239292324938174, 0.9315884316374654, 0.9381525234772328,
    0.943819703739786, 0.9487454974287532, 0.9530532729493237,
    0.9568418680848227, 0.9601911956842573, 0.9631664156831785,
    0.9658210760426529, 0.9681995028427981, 0.9703386372111369,
    0.9722694602755646, 0.9740181081658059, 0.9756067515953744,
    0.9770542950332273, 0.9783769364582924, 0.9795886185234428,
    0.98070139450922, 0.9817257269435768, 0.9826707326601654,
    0.9835443849828098, 0.9843536813867699, 0.9851047832038178,
    0.9858031325674299, 0.9864535507339143, 0.98706032108965,
    0.9876272595079045, 0.9881577742092269, 0.9886549168758498,
    0.989121426449177, 0.9895597667822533, 0.9899721591123003,
    0.9903606101513225, 0.9907269364572184, 0.9910727856373502,
    0.9913996548461292, 0.9917089069639307, 0.9920017847834177,
    0.9922794234786967, 0.9925428615906557, 0.992793050726779,
    0.993030864144429, 0.9932571043620142, 0.9934725099217936,
    0.9936777614106342, 0.9938734868302839, 0.9940602663962188,
    0.9942386368334779, 0.9944090952288196, 0.9945721024907892,
    0.9947280864626282, 0.9948774447272539, 0.9950205471386202,
    0.995157738109532, 0.9952893386823178, 0.9954156484055894,
    0.995536947037561, 0.9956534960940002, 0.9957655402567922,
    0.9958733086572742, 0.9959770160469021, 0.9960768638664075,
    0.9961730412233787, 0.9962657257871197, 0.9963550846086886,
    0.9964412748731768, 0.9965244445905539, 0.9966047332307413,
    0.9966822723080018, 0.9967571859192146, 0.9968295912401459,
    0.9968995989834193, 0.9969673138215269, 0.9970328347778974,
    0.9970962555887455, 0.9971576650381748, 0.9972171472687661,
    0.9972747820696783, 0.997330645144108, 0.9973848083577741,
    0.9974373399699559, 0.9974883048484655, 0.9975377646698231,
    0.9975857781057826, 0.9976324009972657, 0.9976776865166632,
    0.9977216853193847, 0.9977644456854637, 0.9978060136519566,
    0.9978464331368122, 0.9978857460548343, 0.9979239924263115,
    0.9979612104788331, 0.9979974367427831, 0.9980327061409493,
    0.9980670520726644, 0.9981005064928528, 0.9981330999863349,
    0.9981648618377101, 0.9981958200971182, 0.9982260016421507,
    0.9982554322361741, 0.9982841365832935, 0.9983121383801812,
    0.9983394603649702, 0.9983661243634026, 0.9983921513324061,
    0.9984175614012627, 0.9984423739105188
]


def prob_mult_from_e(e: float) -> float:
    """
    returns `k` according to `e` given by this probability algorithm
    ```
        event_count = 0
        p = 1
        while random() < p:
            event_count += 1
            p *= k
    ```
    `e` = expected value of `event_count`
    """
    i_f = e * 4
    i_fl = math.floor(i_f)
    i_ce = math.ceil(i_f)
    if i_ce >= len(_interpolation_table):
        print(f"WARNING: out of bounds for interpolation table: {e} > {(len(_interpolation_table) - 1) / 4}")
        return _interpolation_table[-1]
    else:
        out_diff = _interpolation_table[i_ce] - _interpolation_table[i_fl]
        in_diff = i_f - i_fl
        return _interpolation_table[i_fl] + (out_diff * in_diff)


if __name__ == "__main__":
    # TODO: move things to unit tests
    for i, k in enumerate(_interpolation_table):
        print(f"{i / 4} : {k}")

    print(prob_mult_from_e(7))
    print(prob_mult_from_e(3.3))
    print(_success_until_failure(prob_mult_from_e(3.3)))

    # print(_interpolation_table)

    print(prob_mult_from_e(30))
    print(prob_mult_from_e(31))
    print(prob_mult_from_e(32))
    print(prob_mult_from_e(33))
    print(prob_mult_from_e(34))
    print(_success_until_failure(prob_mult_from_e(34)))

    print(_success_until_failure(prob_mult_from_e(340)))
