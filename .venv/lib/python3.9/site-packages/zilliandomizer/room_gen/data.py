from typing import Dict

from zilliandomizer.room_gen.common import RoomData, TOP_LEFT, TOP_RIGHT, BOT_LEFT, BOT_RIGHT

# TODO: distinguish entrances from exits, and check softlocks from all entrances
# (currently softlock is possible in 0x22 because I only check softlock from 1 entrance)

GEN_ROOMS: Dict[int, RoomData] = {
    0x0a: RoomData([BOT_LEFT, TOP_RIGHT], True, []),
    0x0b: RoomData([TOP_LEFT, BOT_RIGHT], False, []),
    # 0x0d: RoomData([_BOT_LEFT, (1, 9), (1, 10)]),
    0x0f: RoomData([BOT_LEFT], False, []),

    0x10: RoomData([BOT_RIGHT], False, []),
    0x17: RoomData([BOT_LEFT, TOP_LEFT], True, []),

    0x1a: RoomData([BOT_RIGHT, BOT_LEFT, (5, 5)], True, []),
    0x1b: RoomData([BOT_RIGHT, BOT_LEFT], True, []),
    0x1c: RoomData([BOT_RIGHT, BOT_LEFT], True, []),
    0x1d: RoomData([BOT_RIGHT, BOT_LEFT], True, []),

    0x21: RoomData([BOT_LEFT, BOT_RIGHT], True, [(3, 13)]),
    0x22: RoomData([(1, 5), BOT_LEFT, BOT_RIGHT], True, []),
    0x24: RoomData([BOT_LEFT, TOP_RIGHT], True, []),
    0x25: RoomData([TOP_LEFT, BOT_RIGHT], True, []),

    0x29: RoomData([BOT_RIGHT, BOT_LEFT, (5, 7)], True, []),
    0x2b: RoomData([(5, 1), BOT_RIGHT], True, []),
    # 0x2c: RoomData([_BOT_LEFT, _TOP_RIGHT, (1, 11)]),
    0x2d: RoomData([BOT_RIGHT], False, []),
    0x2f: RoomData([BOT_LEFT, BOT_RIGHT], True, []),

    0x31: RoomData([(1, 7), BOT_RIGHT], True, []),
    0x33: RoomData([BOT_RIGHT, BOT_LEFT, (1, 1)], True, []),
    0x34: RoomData([BOT_RIGHT, BOT_LEFT], True, []),
    0x36: RoomData([BOT_RIGHT, BOT_LEFT], True, []),  # 2 in bot right
    0x37: RoomData([TOP_RIGHT, BOT_LEFT], True, []),

    0x39: RoomData([TOP_RIGHT, BOT_LEFT], True, []),
    0x3b: RoomData([BOT_RIGHT, (5, 1)], True, []),
    0x3c: RoomData([BOT_RIGHT, BOT_LEFT], False, []),
    0x3d: RoomData([BOT_RIGHT, BOT_LEFT], True, []),
    0x3e: RoomData([TOP_RIGHT, BOT_RIGHT, BOT_LEFT], True, []),
    0x3f: RoomData([BOT_LEFT, BOT_RIGHT], True, []),

    0x41: RoomData([TOP_LEFT, BOT_RIGHT], False, []),
    0x43: RoomData([(1, 1), BOT_LEFT, BOT_RIGHT], True, []),
    # 0x44 divided
    0x45: RoomData([TOP_RIGHT, BOT_LEFT], True, []),
    0x46: RoomData([BOT_RIGHT, TOP_LEFT], True, []),
    0x47: RoomData([TOP_RIGHT, BOT_LEFT], True, []),

    0x49: RoomData([TOP_RIGHT], True, []),
    0x4b: RoomData([BOT_RIGHT, BOT_LEFT], True, [(3, 0)]),
    0x4c: RoomData([(1, 5), BOT_LEFT, BOT_RIGHT], True, []),
    0x4d: RoomData([BOT_LEFT, BOT_RIGHT], True, []),
    0x4f: RoomData([BOT_LEFT], True, []),

    # 0x51 divided
    0x52: RoomData([BOT_RIGHT, BOT_LEFT], True, []),  # 2 in bot right
    # divided, divided, main, boss

    # 0x59 divided
    0x5a: RoomData([BOT_RIGHT, TOP_RIGHT, TOP_LEFT], True, []),
    0x5b: RoomData([(5, 2), BOT_LEFT, BOT_RIGHT], True, []),
    0x5c: RoomData([BOT_LEFT, BOT_RIGHT, (1, 5)], True, []),
    # divided, divided

    0x61: RoomData([BOT_RIGHT], True, []),
    0x62: RoomData([BOT_RIGHT], True, []),  # 2 in bot right
    0x63: RoomData([BOT_LEFT, BOT_RIGHT, (1, 2)], True, []),
    0x64: RoomData([BOT_LEFT, TOP_RIGHT], True, []),
    # divided, divided

    # 0x69 divided
    0x6a: RoomData([TOP_RIGHT, BOT_LEFT], True, []),  # 2 in top right
    # 0x6b divided
    0x6c: RoomData([(5, 1), TOP_LEFT, BOT_RIGHT], True, []),
    # 0x6d door in middle
    # 0x6e fall from red

    # 0x71 fall
    0x72: RoomData([(5, 1), BOT_LEFT, BOT_RIGHT], True, []),
    0x73: RoomData([BOT_LEFT, (1, 1), BOT_RIGHT, (5, 1)], True, []),
    0x74: RoomData([BOT_LEFT, BOT_RIGHT, (1, 1)], True, []),
    0x75: RoomData([TOP_RIGHT, (5, 1)], True, []),
    # 0x76 divided

    # divided, divided
    0x7c: RoomData([TOP_RIGHT, BOT_LEFT], True, []),
    0x7d: RoomData([(1, 1), BOT_RIGHT], True, []),
    # 0x7e divided

    # 0x82 divided
}
