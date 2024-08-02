"""
09 00, 0c 00 unknown outside
0e 00 ship entrance
10 00 hallway elevator
34 0x hallway bread
39 80 shoot trigger to open door (room 0d)
32 00 mine    y a8 is where y 98 canister sits
14 00-03 enemy
37 00-03 falling enemy
21 ss auto gun
   22 down, moving
   23 right, moving
   24 left, moving
   38 down, not moving
   3a right, not moving
   3b left, not moving
1f ss barrier
   00 horizontal length 1
   01 horizontal length 2
   02 vertical   length 1
   03 vertical   length 1 + small tile (unused?)
   04 vertical   length 2
   05 vertical   length 2 + small tile
   06 horizontal length 1.5
   07 vertical   length 2 - small tile
"""


class SpriteType:
    mine = 0x32
    enemy = 0x14
    falling_enemy = 0x37
    auto_gun = 0x21
    barrier = 0x1f


class AutoGunSub:
    """ direction the auto-gun is facing, and whether it's moving """
    down_move = 0x22
    right_move = 0x23
    left_move = 0x24
    down = 0x38
    right = 0x3a
    left = 0x3b


class BarrierSub:
    """ orientation and length (small tiles) of barrier """
    hor_2 = 0x00
    hor_4 = 0x01
    ver_4 = 0x02
    ver_5 = 0x03
    ver_8 = 0x04
    ver_9 = 0x05
    hor_3 = 0x06
    ver_7 = 0x07
