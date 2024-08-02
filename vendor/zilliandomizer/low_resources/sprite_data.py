from dataclasses import dataclass
from typing import Dict, List, Tuple

from zilliandomizer.low_resources import rom_info


@dataclass
class Sprite:
    """
    6 bytes for each sprite

    rr rr xx yy tt tt

    rr rr: ram address where this sprite goes
    xx: x coord in room
    yy: y coord in room
    tt tt: type of thing

    ```
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
    ```
    """
    ram: int
    """ ram address where this byte is loaded """
    y: int
    x: int
    type: Tuple[int, int]

    def to_bytes(self) -> bytes:
        return bytes([
            self.ram % 256,
            self.ram // 256,
            self.x,
            self.y,
            self.type[0],
            self.type[1]
        ])

    @staticmethod
    def from_bytes(b: bytes) -> "Sprite":
        assert len(b) == 6, f"Sprite data structure in rom should be 6 bytes - found {len(b)}"
        ram_lo, ram_hi, x, y, sprite_type, subtype = b
        return Sprite(
            ram_lo | (ram_hi * 256),
            y,
            x,
            (sprite_type, subtype)
        )


RoomSprites = List[Sprite]
""" all the sprites in 1 room """


sprite_rooms = [
    33222, 33222, 33222, 33223, 33222, 33222, 33236, 33222,
    33255, 33268, 33275, 33282, 33295, 33314, 33222, 33222,
    33327, 33334, 33341, 33354, 33222, 33373, 33380, 33387,
    33406, 33413, 33432, 33439, 33222, 33446, 33459, 33222,
    33466, 33479, 33222, 33486, 33499, 33506, 33531, 33550,
    33569, 33582, 33613, 33620, 33639, 33222, 33676, 33689,
    33708, 33715, 33746, 33753, 33772, 33222, 33803, 33810,
    33853, 33860, 33222, 33222, 33867, 33916, 33947, 33960,
    33222, 33967, 33980, 33987, 34006, 34013, 34014, 34051,
    33222, 34082, 34125, 34138, 34145, 34170, 34189, 34190,
    33222, 34221, 34246, 34259, 34284, 33222, 34315, 34334,
    34347, 34354, 34367, 34392, 34423, 34442, 34479, 33222,
    33222, 34516, 34553, 34584, 34609, 34640, 34671, 33222,
    34678, 34685, 34710, 34741, 34796, 34827, 34870, 34889,
    34902, 34909, 33222, 34928, 34947, 33222, 34978, 35027,
    33222, 35034, 35047, 35084, 35103, 35140, 35171, 35202,
    35209, 35216, 35235, 33222, 35254, 33222, 35267, 35280
]
"""
iterable that gives the address to the sprite data in each room

index is map_index
"""


data: Dict[int, RoomSprites] = {
    0: [],
    1: [],
    2: [],
    3: [Sprite(ram=50112, y=96, x=8, type=(14, 0)),
        Sprite(ram=50272, y=16, x=112, type=(9, 0))],
    4: [],
    5: [],
    6: [Sprite(ram=50016, y=152, x=144, type=(16, 0)),
        Sprite(ram=50272, y=16, x=16, type=(9, 0)),
        Sprite(ram=50080, y=0, x=128, type=(12, 0))],
    7: [],
    8: [Sprite(ram=50272, y=168, x=48, type=(52, 2)),
        Sprite(ram=50432, y=152, x=152, type=(20, 0))],
    9: [Sprite(ram=50016, y=152, x=80, type=(16, 0))],
    10: [Sprite(ram=50272, y=64, x=72, type=(31, 4))],
    11: [Sprite(ram=50432, y=152, x=48, type=(20, 0)),
         Sprite(ram=50464, y=152, x=16, type=(20, 0))],
    12: [Sprite(ram=50272, y=168, x=80, type=(50, 0)),
         Sprite(ram=50304, y=168, x=160, type=(50, 0)),
         Sprite(ram=50432, y=152, x=192, type=(20, 1))],
    13: [Sprite(ram=50272, y=8, x=96, type=(31, 4)),
         Sprite(ram=50304, y=96, x=240, type=(57, 128))],
    14: [],
    15: [],
    16: [Sprite(ram=50432, y=152, x=48, type=(20, 0))],
    17: [Sprite(ram=50016, y=152, x=80, type=(16, 0))],
    18: [Sprite(ram=50272, y=168, x=80, type=(50, 0)),
         Sprite(ram=50304, y=168, x=160, type=(50, 0))],
    19: [Sprite(ram=50336, y=168, x=80, type=(50, 0)),
         Sprite(ram=50432, y=152, x=80, type=(20, 0)),
         Sprite(ram=50464, y=152, x=128, type=(20, 0))],
    20: [],
    21: [Sprite(ram=50432, y=152, x=112, type=(20, 0))],
    22: [Sprite(ram=50016, y=152, x=144, type=(16, 0))],
    23: [Sprite(ram=50272, y=64, x=80, type=(31, 2)),
         Sprite(ram=50432, y=152, x=144, type=(20, 0))],
    24: [Sprite(ram=50016, y=152, x=80, type=(16, 0))],
    25: [Sprite(ram=50304, y=152, x=80, type=(20, 0)),
         Sprite(ram=50336, y=152, x=112, type=(20, 0)),
         Sprite(ram=50368, y=152, x=144, type=(20, 0))],
    26: [Sprite(ram=50272, y=128, x=120, type=(31, 4))],
    27: [Sprite(ram=50304, y=64, x=120, type=(31, 4))],
    28: [],
    29: [Sprite(ram=50336, y=0, x=128, type=(31, 4)),
         Sprite(ram=50432, y=152, x=72, type=(20, 0))],
    30: [Sprite(ram=50016, y=152, x=144, type=(16, 0))],
    31: [],
    32: [Sprite(ram=50016, y=152, x=80, type=(16, 0)),
         Sprite(ram=50432, y=152, x=128, type=(20, 0))],
    33: [Sprite(ram=50272, y=0, x=80, type=(31, 4))],
    34: [],
    35: [Sprite(ram=50432, y=152, x=112, type=(20, 1)),
         Sprite(ram=50464, y=152, x=144, type=(20, 1))],
    36: [Sprite(ram=50272, y=56, x=64, type=(31, 1))],
    37: [Sprite(ram=50304, y=64, x=168, type=(31, 4)),
         Sprite(ram=50432, y=152, x=128, type=(20, 1)),
         Sprite(ram=50464, y=152, x=160, type=(20, 1)),
         Sprite(ram=50496, y=152, x=192, type=(20, 1))],
    38: [Sprite(ram=50016, y=152, x=144, type=(16, 0)),
         Sprite(ram=50432, y=152, x=48, type=(20, 0)),
         Sprite(ram=50464, y=152, x=80, type=(20, 0))],
    39: [Sprite(ram=50016, y=152, x=144, type=(16, 0)),
         Sprite(ram=50496, y=152, x=64, type=(20, 1)),
         Sprite(ram=50528, y=152, x=96, type=(20, 1))],
    40: [Sprite(ram=50016, y=152, x=80, type=(16, 0)),
         Sprite(ram=50432, y=152, x=168, type=(20, 3))],
    41: [Sprite(ram=50272, y=80, x=72, type=(33, 35)),
         Sprite(ram=50304, y=128, x=160, type=(33, 35)),
         Sprite(ram=50336, y=128, x=192, type=(33, 34)),
         Sprite(ram=50368, y=120, x=72, type=(31, 6)),
         Sprite(ram=50400, y=56, x=112, type=(31, 1))],
    42: [Sprite(ram=50016, y=152, x=80, type=(16, 0))],
    43: [Sprite(ram=50272, y=104, x=96, type=(50, 0)),
         Sprite(ram=50432, y=152, x=128, type=(20, 2)),
         Sprite(ram=50464, y=152, x=160, type=(20, 2))],
    44: [Sprite(ram=50304, y=64, x=128, type=(31, 4)),
         Sprite(ram=50336, y=96, x=16, type=(33, 58)),
         Sprite(ram=50368, y=0, x=136, type=(33, 34)),
         Sprite(ram=50400, y=136, x=224, type=(33, 36)),
         Sprite(ram=50432, y=24, x=96, type=(20, 3)),
         Sprite(ram=50464, y=24, x=128, type=(20, 3))],
    45: [],
    46: [Sprite(ram=50016, y=152, x=144, type=(16, 0)),
         Sprite(ram=50272, y=168, x=56, type=(50, 0))],
    47: [Sprite(ram=50304, y=120, x=208, type=(31, 1)),
         Sprite(ram=50432, y=152, x=104, type=(20, 3)),
         Sprite(ram=50464, y=152, x=120, type=(20, 3))],
    48: [Sprite(ram=50272, y=152, x=120, type=(52, 1))],
    49: [Sprite(ram=50272, y=120, x=80, type=(31, 0)),
         Sprite(ram=50304, y=120, x=160, type=(31, 0)),
         Sprite(ram=50432, y=24, x=32, type=(20, 2)),
         Sprite(ram=50464, y=24, x=192, type=(20, 2)),
         Sprite(ram=50496, y=152, x=192, type=(20, 3))],
    50: [Sprite(ram=50016, y=152, x=80, type=(16, 0))],
    51: [Sprite(ram=50304, y=0, x=96, type=(31, 5)),
         Sprite(ram=50336, y=104, x=208, type=(50, 0)),
         Sprite(ram=50432, y=152, x=72, type=(20, 2))],
    52: [Sprite(ram=50272, y=56, x=16, type=(33, 35)),
         Sprite(ram=50368, y=64, x=144, type=(33, 34)),
         Sprite(ram=50400, y=104, x=112, type=(50, 0)),
         Sprite(ram=50336, y=40, x=144, type=(50, 0)),
         Sprite(ram=50432, y=152, x=152, type=(20, 2))],
    53: [],
    54: [Sprite(ram=50272, y=0, x=112, type=(33, 34))],
    55: [Sprite(ram=50272, y=104, x=40, type=(50, 0)),
         Sprite(ram=50304, y=104, x=104, type=(50, 0)),
         Sprite(ram=50336, y=104, x=168, type=(50, 0)),
         Sprite(ram=50368, y=40, x=72, type=(50, 0)),
         Sprite(ram=50400, y=40, x=136, type=(50, 0)),
         Sprite(ram=50432, y=152, x=96, type=(20, 2)),
         Sprite(ram=50464, y=152, x=128, type=(20, 2))],
    56: [Sprite(ram=50016, y=152, x=80, type=(16, 0))],
    57: [Sprite(ram=50336, y=64, x=40, type=(31, 4))],
    58: [],
    59: [],
    60: [Sprite(ram=50272, y=0, x=56, type=(33, 34)),
         Sprite(ram=50304, y=0, x=104, type=(33, 34)),
         Sprite(ram=50336, y=0, x=160, type=(33, 34)),
         Sprite(ram=50368, y=64, x=56, type=(33, 34)),
         Sprite(ram=50400, y=64, x=144, type=(33, 34)),
         Sprite(ram=50432, y=64, x=184, type=(33, 34)),
         Sprite(ram=50464, y=128, x=88, type=(33, 34)),
         Sprite(ram=50496, y=128, x=152, type=(33, 34))],
    61: [Sprite(ram=50272, y=64, x=32, type=(33, 34)),
         Sprite(ram=50304, y=64, x=72, type=(33, 34)),
         Sprite(ram=50336, y=0, x=112, type=(33, 34)),
         Sprite(ram=50368, y=64, x=168, type=(33, 34)),
         Sprite(ram=50400, y=40, x=168, type=(50, 0))],
    62: [Sprite(ram=50304, y=168, x=72, type=(50, 0)),
         Sprite(ram=50432, y=152, x=160, type=(20, 2))],
    63: [Sprite(ram=50464, y=96, x=40, type=(55, 2))],
    64: [],
    65: [Sprite(ram=50272, y=96, x=16, type=(33, 35)),
         Sprite(ram=50304, y=48, x=224, type=(33, 36))],
    66: [Sprite(ram=50016, y=152, x=80, type=(16, 0))],
    67: [Sprite(ram=50272, y=72, x=16, type=(33, 58)),
         Sprite(ram=50304, y=104, x=16, type=(33, 58)),
         Sprite(ram=50432, y=152, x=192, type=(20, 1))],
    68: [Sprite(ram=50336, y=128, x=120, type=(31, 4))],
    69: [],
    70: [Sprite(ram=50272, y=72, x=16, type=(33, 35)),
         Sprite(ram=50304, y=128, x=16, type=(33, 35)),
         Sprite(ram=50336, y=168, x=32, type=(50, 0)),
         Sprite(ram=50368, y=168, x=88, type=(50, 0)),
         Sprite(ram=50400, y=168, x=144, type=(50, 0)),
         Sprite(ram=50560, y=168, x=200, type=(50, 0))],
    71: [Sprite(ram=50272, y=0, x=24, type=(31, 4)),
         Sprite(ram=50304, y=64, x=72, type=(33, 34)),
         Sprite(ram=50336, y=64, x=120, type=(33, 34)),
         Sprite(ram=50368, y=168, x=144, type=(50, 0)),
         Sprite(ram=50432, y=88, x=192, type=(20, 0))],
    72: [],
    73: [Sprite(ram=50304, y=104, x=56, type=(50, 0)),
         Sprite(ram=50336, y=72, x=88, type=(50, 0)),
         Sprite(ram=50400, y=128, x=80, type=(31, 4)),
         Sprite(ram=50432, y=96, x=120, type=(31, 5)),
         Sprite(ram=50464, y=64, x=144, type=(31, 4)),
         Sprite(ram=50496, y=120, x=16, type=(20, 2)),
         Sprite(ram=50528, y=152, x=176, type=(20, 3))],
    74: [Sprite(ram=50016, y=152, x=80, type=(16, 0)),
         Sprite(ram=50272, y=152, x=72, type=(52, 4))],
    75: [Sprite(ram=50304, y=8, x=88, type=(31, 4))],
    76: [Sprite(ram=50272, y=32, x=16, type=(33, 58)),
         Sprite(ram=50368, y=168, x=64, type=(50, 0)),
         Sprite(ram=50400, y=168, x=144, type=(50, 0)),
         Sprite(ram=50432, y=152, x=192, type=(20, 3))],
    77: [Sprite(ram=50304, y=64, x=112, type=(31, 1)),
         Sprite(ram=50336, y=64, x=160, type=(31, 1)),
         Sprite(ram=50464, y=152, x=128, type=(20, 2))],
    78: [],
    79: [Sprite(ram=50272, y=64, x=56, type=(31, 4)),
         Sprite(ram=50304, y=64, x=96, type=(31, 4)),
         Sprite(ram=50336, y=64, x=136, type=(31, 4)),
         Sprite(ram=50368, y=64, x=176, type=(31, 4)),
         Sprite(ram=50400, y=136, x=224, type=(33, 36))],
    80: [],
    81: [Sprite(ram=50272, y=0, x=160, type=(33, 34)),
         Sprite(ram=50304, y=48, x=224, type=(33, 36)),
         Sprite(ram=50432, y=88, x=48, type=(20, 3)),
         Sprite(ram=50464, y=88, x=88, type=(20, 2))],
    82: [Sprite(ram=50336, y=72, x=64, type=(50, 0)),
         Sprite(ram=50368, y=72, x=176, type=(50, 0))],
    83: [Sprite(ram=50272, y=64, x=64, type=(33, 34)),
         Sprite(ram=50304, y=64, x=176, type=(33, 34)),
         Sprite(ram=50432, y=24, x=120, type=(20, 3)),
         Sprite(ram=50464, y=24, x=144, type=(20, 3))],
    84: [Sprite(ram=50272, y=136, x=64, type=(50, 0)),
         Sprite(ram=50304, y=40, x=112, type=(50, 0)),
         Sprite(ram=50368, y=0, x=88, type=(33, 34)),
         Sprite(ram=50400, y=32, x=224, type=(33, 36)),
         Sprite(ram=50432, y=152, x=208, type=(20, 3))],
    85: [],
    86: [Sprite(ram=50432, y=152, x=128, type=(20, 2)),
         Sprite(ram=50464, y=152, x=160, type=(20, 2)),
         Sprite(ram=50496, y=152, x=192, type=(20, 2))],
    87: [Sprite(ram=50016, y=152, x=144, type=(16, 0)),
         Sprite(ram=50496, y=152, x=64, type=(20, 2))],
    88: [Sprite(ram=50016, y=152, x=80, type=(16, 0))],
    89: [Sprite(ram=50432, y=152, x=104, type=(20, 3)),
         Sprite(ram=50464, y=152, x=128, type=(20, 3))],
    90: [Sprite(ram=50272, y=112, x=16, type=(33, 35)),
         Sprite(ram=50304, y=48, x=40, type=(33, 36)),
         Sprite(ram=50400, y=88, x=32, type=(31, 6)),
         Sprite(ram=50432, y=152, x=104, type=(20, 2))],
    91: [Sprite(ram=50272, y=168, x=80, type=(50, 0)),
         Sprite(ram=50304, y=168, x=160, type=(50, 0)),
         Sprite(ram=50336, y=0, x=112, type=(33, 56)),
         Sprite(ram=50368, y=32, x=224, type=(33, 59)),
         Sprite(ram=50432, y=152, x=144, type=(20, 3))],
    92: [Sprite(ram=50272, y=168, x=80, type=(50, 0)),
         Sprite(ram=50400, y=168, x=144, type=(50, 0)),
         Sprite(ram=50432, y=152, x=80, type=(20, 2))],
    93: [Sprite(ram=50272, y=16, x=96, type=(33, 36)),
         Sprite(ram=50304, y=32, x=128, type=(33, 35)),
         Sprite(ram=50336, y=88, x=16, type=(31, 1)),
         Sprite(ram=50368, y=120, x=112, type=(31, 1)),
         Sprite(ram=50432, y=152, x=144, type=(20, 3)),
         Sprite(ram=50464, y=152, x=168, type=(20, 3))],
    94: [Sprite(ram=50272, y=64, x=48, type=(33, 35)),
         Sprite(ram=50304, y=96, x=80, type=(33, 35)),
         Sprite(ram=50336, y=128, x=112, type=(33, 35)),
         Sprite(ram=50368, y=64, x=160, type=(33, 34)),
         Sprite(ram=50400, y=64, x=192, type=(33, 34)),
         Sprite(ram=50432, y=88, x=24, type=(55, 3))],
    95: [],
    96: [],
    97: [Sprite(ram=50272, y=0, x=112, type=(33, 34)),
         Sprite(ram=50304, y=120, x=16, type=(31, 1)),
         Sprite(ram=50336, y=56, x=208, type=(31, 1)),
         Sprite(ram=50432, y=24, x=144, type=(20, 3)),
         Sprite(ram=50464, y=88, x=96, type=(20, 3)),
         Sprite(ram=50496, y=152, x=160, type=(20, 3))],
    98: [Sprite(ram=50272, y=64, x=48, type=(33, 34)),
         Sprite(ram=50304, y=128, x=80, type=(33, 34)),
         Sprite(ram=50336, y=0, x=104, type=(33, 34)),
         Sprite(ram=50368, y=88, x=160, type=(31, 0)),
         Sprite(ram=50400, y=168, x=176, type=(50, 0))],
    99: [Sprite(ram=50272, y=64, x=16, type=(33, 34)),
         Sprite(ram=50400, y=104, x=96, type=(50, 0)),
         Sprite(ram=50432, y=80, x=40, type=(55, 2)),
         Sprite(ram=50464, y=96, x=48, type=(55, 2))],
    100: [Sprite(ram=50272, y=168, x=128, type=(50, 0)),
          Sprite(ram=50304, y=64, x=64, type=(33, 56)),
          Sprite(ram=50336, y=0, x=96, type=(33, 56)),
          Sprite(ram=50368, y=64, x=112, type=(33, 56)),
          Sprite(ram=50432, y=152, x=128, type=(20, 2))],
    101: [Sprite(ram=50336, y=24, x=160, type=(20, 3)),
          Sprite(ram=50400, y=24, x=144, type=(20, 3)),
          Sprite(ram=50432, y=152, x=104, type=(20, 2)),
          Sprite(ram=50464, y=152, x=128, type=(20, 2)),
          Sprite(ram=50496, y=152, x=160, type=(20, 2))],
    102: [Sprite(ram=50304, y=0, x=112, type=(33, 34))],
    103: [],
    104: [Sprite(ram=50016, y=24, x=80, type=(16, 0))],
    105: [Sprite(ram=50336, y=168, x=80, type=(50, 0)),
          Sprite(ram=50368, y=168, x=96, type=(50, 0)),
          Sprite(ram=50400, y=56, x=80, type=(31, 0)),
          Sprite(ram=50432, y=136, x=112, type=(31, 7))],
    106: [Sprite(ram=50272, y=168, x=64, type=(50, 0)),
          Sprite(ram=50304, y=168, x=96, type=(50, 0)),
          Sprite(ram=50368, y=168, x=160, type=(50, 0)),
          Sprite(ram=50400, y=0, x=112, type=(33, 34)),
          Sprite(ram=50432, y=152, x=128, type=(20, 3))],
    107: [Sprite(ram=50272, y=64, x=48, type=(33, 34)),
          Sprite(ram=50304, y=64, x=96, type=(33, 34)),
          Sprite(ram=50336, y=64, x=136, type=(33, 34)),
          Sprite(ram=50368, y=40, x=80, type=(50, 0)),
          Sprite(ram=50400, y=40, x=112, type=(50, 0)),
          Sprite(ram=50432, y=40, x=160, type=(50, 0)),
          Sprite(ram=50528, y=152, x=104, type=(20, 2)),
          Sprite(ram=50464, y=152, x=128, type=(20, 2)),
          Sprite(ram=50496, y=152, x=152, type=(20, 2))],
    108: [Sprite(ram=50272, y=96, x=56, type=(33, 34)),
          Sprite(ram=50304, y=0, x=88, type=(33, 34)),
          Sprite(ram=50336, y=128, x=112, type=(33, 34)),
          Sprite(ram=50368, y=0, x=152, type=(33, 34)),
          Sprite(ram=50432, y=120, x=176, type=(20, 2))],
    109: [Sprite(ram=50272, y=0, x=96, type=(33, 34)),
          Sprite(ram=50304, y=64, x=168, type=(33, 36)),
          Sprite(ram=50336, y=24, x=224, type=(33, 36)),
          Sprite(ram=50368, y=168, x=104, type=(50, 0)),
          Sprite(ram=50400, y=40, x=112, type=(50, 0)),
          Sprite(ram=50432, y=80, x=40, type=(55, 2)),
          Sprite(ram=50464, y=96, x=48, type=(55, 2))],
    110: [Sprite(ram=50336, y=168, x=32, type=(50, 0)),
          Sprite(ram=50432, y=152, x=168, type=(20, 3)),
          Sprite(ram=50464, y=152, x=192, type=(20, 3))],
    111: [Sprite(ram=50016, y=24, x=144, type=(16, 0)),
          Sprite(ram=50432, y=24, x=104, type=(20, 3))],
    112: [Sprite(ram=50016, y=152, x=80, type=(16, 0))],
    113: [Sprite(ram=50336, y=168, x=32, type=(50, 0)),
          Sprite(ram=50304, y=168, x=80, type=(50, 0)),
          Sprite(ram=50272, y=168, x=128, type=(50, 0))],
    114: [],
    115: [Sprite(ram=50272, y=168, x=96, type=(50, 0)),
          Sprite(ram=50304, y=168, x=152, type=(50, 0)),
          Sprite(ram=50368, y=168, x=208, type=(50, 0))],
    116: [Sprite(ram=50400, y=64, x=64, type=(33, 34)),
          Sprite(ram=50336, y=104, x=112, type=(50, 0)),
          Sprite(ram=50272, y=8, x=224, type=(33, 36)),
          Sprite(ram=50432, y=80, x=40, type=(55, 2)),
          Sprite(ram=50464, y=96, x=48, type=(55, 2))],
    117: [],
    118: [Sprite(ram=50272, y=0, x=104, type=(33, 34)),
          Sprite(ram=50304, y=104, x=112, type=(50, 0)),
          Sprite(ram=50336, y=168, x=112, type=(50, 0)),
          Sprite(ram=50368, y=104, x=160, type=(50, 0)),
          Sprite(ram=50400, y=168, x=208, type=(50, 0)),
          Sprite(ram=50432, y=168, x=160, type=(50, 0)),
          Sprite(ram=50464, y=88, x=80, type=(20, 3)),
          Sprite(ram=50496, y=88, x=104, type=(20, 3))],
    119: [Sprite(ram=50016, y=152, x=144, type=(16, 0))],
    120: [],
    121: [Sprite(ram=50016, y=152, x=144, type=(16, 0)),
          Sprite(ram=50432, y=152, x=208, type=(20, 3))],
    122: [Sprite(ram=50272, y=104, x=128, type=(33, 34)),
          Sprite(ram=50304, y=24, x=224, type=(33, 36)),
          Sprite(ram=50336, y=64, x=176, type=(33, 36)),
          Sprite(ram=50368, y=80, x=128, type=(50, 0)),
          Sprite(ram=50400, y=80, x=144, type=(50, 0)),
          Sprite(ram=50432, y=152, x=96, type=(20, 2))],
    123: [Sprite(ram=50400, y=64, x=80, type=(33, 34)),
          Sprite(ram=50432, y=152, x=120, type=(20, 2)),
          Sprite(ram=50464, y=152, x=144, type=(20, 2))],
    124: [Sprite(ram=50336, y=0, x=104, type=(33, 34)),
          Sprite(ram=50368, y=64, x=144, type=(33, 34)),
          Sprite(ram=50400, y=40, x=16, type=(50, 0)),
          Sprite(ram=50272, y=104, x=96, type=(50, 0)),
          Sprite(ram=50304, y=104, x=144, type=(50, 0)),
          Sprite(ram=50432, y=168, x=144, type=(50, 0))],
    125: [Sprite(ram=50336, y=96, x=32, type=(33, 34)),
          Sprite(ram=50368, y=88, x=80, type=(31, 0)),
          Sprite(ram=50304, y=120, x=80, type=(31, 1)),
          Sprite(ram=50432, y=88, x=120, type=(20, 2)),
          Sprite(ram=50464, y=88, x=144, type=(20, 2))],
    126: [Sprite(ram=50272, y=96, x=56, type=(33, 34)),
          Sprite(ram=50304, y=128, x=96, type=(33, 34)),
          Sprite(ram=50336, y=168, x=144, type=(33, 59)),
          Sprite(ram=50368, y=64, x=176, type=(33, 34)),
          Sprite(ram=50400, y=16, x=224, type=(33, 36))],
    127: [Sprite(ram=50016, y=152, x=144, type=(16, 0))],
    128: [Sprite(ram=50016, y=152, x=80, type=(16, 0))],
    129: [Sprite(ram=50016, y=152, x=144, type=(16, 0)),
          Sprite(ram=50432, y=152, x=64, type=(20, 1)),
          Sprite(ram=50464, y=152, x=96, type=(20, 1))],
    130: [Sprite(ram=50272, y=64, x=80, type=(33, 34)),
          Sprite(ram=50432, y=152, x=144, type=(20, 1)),
          Sprite(ram=50464, y=152, x=168, type=(20, 1))],
    131: [],
    132: [Sprite(ram=50432, y=152, x=128, type=(20, 1)),
          Sprite(ram=50464, y=152, x=160, type=(20, 1))],
    133: [],
    134: [Sprite(ram=50432, y=152, x=112, type=(20, 1)),
          Sprite(ram=50464, y=152, x=144, type=(20, 1))],
    135: [Sprite(ram=50016, y=152, x=144, type=(16, 0))]
}


def make_sprite_rooms(o: bytes) -> None:
    """ iterator that gives the address to the sprite data in each room """
    out: List[int] = []
    for map_index in range(136):
        room_pointer = rom_info.np_sprites_80b6 + 2 * map_index
        room_addr_lo = o[room_pointer]
        room_addr_hi = o[room_pointer + 1]
        out.append((room_addr_hi * 256) | room_addr_lo)
    print(out)


def make_sprite_data(o: bytes) -> None:
    data: Dict[int, RoomSprites] = {}

    for map_index, room_address in enumerate(sprite_rooms):
        room_sprites: RoomSprites = []
        count = o[room_address]
        for sprite_no in range(count):
            sprite_address = room_address + 1 + 6 * sprite_no
            room_sprites.append(Sprite.from_bytes(
                o[sprite_address:sprite_address + 6]
            ))
        data[map_index] = room_sprites
    from pprint import pprint
    pprint(data)
