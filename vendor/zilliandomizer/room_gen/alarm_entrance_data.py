from dataclasses import dataclass
from typing import List, Optional

from zilliandomizer.low_resources import rom_info


@dataclass
class AlarmEntrance:
    ceiling: bool
    x: int
    level: int
    """ the level of the enemy that enters """


indexes = [
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 6, 0, 0, 0, 12,
    0, 0, 0, 0, 0, 0, 0, 18,
    0, 0, 6, 0, 6, 0, 0, 0,
    0, 36, 42, 0, 24, 0, 0, 0,
    0, 0, 0, 0, 30, 54, 0, 24,
    0, 0, 0, 48, 0, 0, 0, 0,
    0, 54, 0, 30, 0, 54, 0, 36,
    0, 60, 0, 36, 24, 60, 0, 0,
    0, 0, 0, 36, 0, 24, 0, 24,
    0, 78, 84, 0, 90, 0, 0, 0,
    0, 90, 66, 90, 0, 0, 0, 0,
    0, 0, 0, 0, 78, 0, 72, 0,
    0, 66, 0, 0, 0, 0, 72, 0,
    0, 0, 78, 0, 0, 78, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0
]

data = [
    AlarmEntrance(ceiling=False, x=8, level=0),
    AlarmEntrance(ceiling=True, x=136, level=0),
    AlarmEntrance(ceiling=False, x=240, level=0),
    AlarmEntrance(ceiling=False, x=240, level=1),
    AlarmEntrance(ceiling=False, x=8, level=1),
    AlarmEntrance(ceiling=True, x=144, level=1),
    AlarmEntrance(ceiling=True, x=80, level=1),
    AlarmEntrance(ceiling=True, x=48, level=1),
    AlarmEntrance(ceiling=True, x=112, level=1),
    AlarmEntrance(ceiling=True, x=216, level=1),
    AlarmEntrance(ceiling=False, x=8, level=2),
    AlarmEntrance(ceiling=False, x=240, level=2),
    AlarmEntrance(ceiling=True, x=80, level=2),
    AlarmEntrance(ceiling=True, x=120, level=2),
    AlarmEntrance(ceiling=True, x=192, level=2),
    None
]


def generate_data(o: bytes) -> None:
    indexes = list(o[
        rom_info.alarmed_enemy_entrance_table_7f04:
        rom_info.alarmed_enemy_entrance_table_7f04 + 136
    ])
    data: List[Optional[AlarmEntrance]] = []
    for i in range(16):
        address = rom_info.alarmed_enemy_entrance_data_7f86 + (6 * (i + 1))
        x = o[address]
        if x != 0 and x != 0xff:
            level = o[address + 4]
            ceiling = o[address + 1] == 0xa0
            data.append(AlarmEntrance(ceiling, x, level))
        else:  # null
            data.append(None)
    print(indexes)
    print(data)
