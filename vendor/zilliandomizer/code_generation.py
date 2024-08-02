"""
I used code to generate python code for location and region data.
Most of it is outdated and will not generate the correct format for the current code.
"""

from typing import List, Dict, Set
from zilliandomizer.logic_components.items import KEYWORD, NORMAL, RESCUE, MAIN
from zilliandomizer.low_resources import rom_info
from zilliandomizer.utils import make_loc_name, ItemData
from zilliandomizer.patch import Patcher  # for access to rom data
from zilliandomizer.logic_components.location_data import make_locations
from zilliandomizer.utils.loc_name_matcher import all_locations_in_room
from zilliandomizer.utils import make_room_name


def make_location_code() -> None:
    p = Patcher()
    locs: List[str] = []
    room_no = 0
    for room in p.get_item_rooms():
        for item in p.get_items(room):
            if item.code in {KEYWORD, NORMAL, RESCUE, MAIN}:
                name = make_loc_name(room_no, item)
                if name.startswith("x"):
                    name = "0" + name[1:]
                locs.append(f'    "{name}": Location("{name}", Req(gun={item.gun + 1})),')
        room_no += 1
    for loc in locs:
        print(loc)


def region_code_maker() -> None:
    """ outdated way of creating code for `region_data` """
    locations = make_locations()

    rooms: Dict[str, Set[str]] = {}
    for key in locations:
        room = key[:5]
        if not (room in rooms):
            rooms[room] = set()
        rooms[room].add(key)

    # can't print these as we go because neighbor object might not be made yet
    connections: List[str] = []

    for room in rooms:
        split = room.split('c')
        col = int(split[1])
        row = int(split[0][1:])

        print()
        print(f'{room} = Region("{room}")')
        for loc in rooms[room]:
            print(f'{room}.locations.add(locations["{loc}"])')

        # .connections.add((r01c7, Req(door=23)))
        room_no = row * 8 + col

        up = room_no - 8
        if up > 0:
            r = up // 8
            conn = f"r{r if r > 9 else '0' + str(r)}c{up % 8}"
            if conn in rooms:
                connections.append(f'{room}.connections.add(({conn}, Req(door={room_no})))')
        down = room_no + 8
        if down < 136:
            r = down // 8
            conn = f"r{r if r > 9 else '0' + str(r)}c{down % 8}"
            if conn in rooms:
                connections.append(f'{room}.connections.add(({conn}, Req(door={room_no})))')
        left = room_no - 1
        if left % 8 != 7:
            r = left // 8
            conn = f"r{r if r > 9 else '0' + str(r)}c{left % 8}"
            if conn in rooms:
                connections.append(f'{room}.connections.add(({conn}, Req(door={room_no})))')
        right = room_no + 1
        if right % 8 != 0:
            r = right // 8
            conn = f"r{r if r > 9 else '0' + str(r)}c{right % 8}"
            if conn in rooms:
                connections.append(f'{room}.connections.add(({conn}, Req(door={room_no})))')

    print()
    for connection in connections:
        print(connection)


def add_doors_to_regions() -> None:
    lines: List[str]
    with open("src/region_data.py") as file:
        lines = file.readlines()
    for i, line in enumerate(lines):
        split1 = line.split('Region("r')
        if len(split1) > 1:
            room_coords = split1[1][:-3]
            split2 = room_coords.split('c')
            try:
                room_no = int(split2[0]) * 8 + int(split2[1])
                new_line = line[:-2] + f", {room_no})\n"
                lines[i] = new_line
            except ValueError:
                pass  # ignore divided rooms
    with open("src/region_data.py", "w") as file:
        file.writelines(lines)


def location_ids() -> None:
    p = Patcher()
    loc_to_id: List[str] = []
    id_to_loc: List[str] = []
    room_no = 0
    for room in p.get_item_rooms():
        for item in p.get_items(room):
            if item.code in {KEYWORD, NORMAL, RESCUE, MAIN}:
                name = make_loc_name(room_no, item)
                # item.room_code is even number for each room that has items
                # 0 in both r01c2 and main,
                # but main has 0 in item.mask so still unique
                loc_id = (item.room_code << 7) | (item.mask)
                loc_to_id.append(f'    "{name}": {loc_id},')
                id_to_loc.append(f'    {loc_id}: "{name}",')
        room_no += 1

    print('loc_to_id: Dict[str, int] = {')
    for loc in loc_to_id:
        print(loc)
    print('}\n')

    print('id_to_loc: Dict[int, str] = {')
    for loc in id_to_loc:
        print(loc)
    print('}\n')


def big_location_ids() -> None:
    p = Patcher()
    loc_to_id: List[str] = []
    id_to_loc: List[str] = []
    count_item_rooms = 0
    for map_index, room in enumerate(p.get_item_rooms()):
        row = map_index // 8
        col = map_index & 7
        item_count = p.rom[room]
        print(f"{map_index}: {item_count}")
        if item_count == 0:
            continue
        item = ItemData(*p.rom[room + 1: room + 9])
        if item.code not in {KEYWORD, NORMAL, RESCUE}:
            continue
        item_room_index = item.room_code // 2
        assert item_room_index == count_item_rooms, f"{map_index} {item.room_code} {count_item_rooms}"
        """
        for row, y in enumerate(range(0x18, 0x99, 0x20)):  # 0x18, 0x38, 0x58, 0x78, 0x98
            for col, x in enumerate(range(0x10, 0xe1, 0x10)):  # 0x10, 0x20, ... , 0xe0
                location_id = item_room_index * 5 * 14 + row * 14 + col
                location_name = make_loc_name(map_index, y, x)
                loc_to_id.append(f'    "{location_name}": {location_id},')
                id_to_loc.append(f'    {location_id}: "{location_name}",')
        """
        for in_room in all_locations_in_room():
            location_id = len(loc_to_id)
            location_name = f"{make_room_name(row, col)} {in_room}"
            loc_to_id.append(f'    "{location_name}": {location_id},')
            id_to_loc.append(f'    {location_id}: "{location_name}",')

        count_item_rooms += 1
    print(f"item room count: {count_item_rooms}")

    with open("src/zilliandomizer/low_resources/new_loc_id_maps.py", "wt") as file:
        file.write('loc_to_id: Dict[str, int] = {\n')
        for loc in loc_to_id:
            file.write(loc)
            file.write('\n')
        file.write('}\n\n')

        file.write('id_to_loc: Dict[int, str] = {\n')
        for loc in id_to_loc:
            file.write(loc)
            file.write('\n')
        file.write('}\n\n')


def item_room_codes() -> None:
    p = Patcher()
    for map_index, room in enumerate(p.get_item_rooms()):
        item_count = p.rom[room]
        if item_count == 0:
            continue
        item = ItemData(*p.rom[room + 1: room + 9])
        if item.code not in {KEYWORD, NORMAL, RESCUE}:
            continue
        print(f"    0x{map_index:02x}: 0x{item.room_code:02x},")


def weird_vanilla_locations() -> None:
    from zilliandomizer.utils.loc_name_maps import loc_to_id
    p = Patcher()
    for map_index, room in enumerate(p.get_item_rooms()):
        for item in p.get_items(room):
            if item.code in {KEYWORD, NORMAL, RESCUE, MAIN}:
                name = make_loc_name(map_index, item)
                if name not in loc_to_id:
                    print(name)


def region_file_edit() -> None:
    lines: List[str] = []
    with open("src/zilliandomizer/logic_components/region_data.py", "r") as file:
        reg_name = ""
        loc_count = 0
        for line in file:
            split = line.strip().split(' = Region("')
            if len(split) == 2 and len(split[0]) == 5:
                reg_name = split[0]
                loc_count = 0

            if line.startswith(f'    {reg_name}.locations.append(locations["r'):
                loc_count += 1
            else:  # not adding a location to a region
                if loc_count > 0:
                    lines.append(f'    assert len(reg_name_to_loc_name["{reg_name}"]) == {loc_count}\n')
                    lines.append(f'    for loc_name in reg_name_to_loc_name["{reg_name}"]:\n')
                    lines.append(f'        {reg_name}.locations.append(locations[loc_name])\n')

                    loc_count = 0
                lines.append(line)

    with open("src/zilliandomizer/logic_components/region_data_new.py", "x") as file:
        file.writelines(lines)


def doors_d() -> None:
    from collections import defaultdict
    from pprint import pp
    BANK_4_OFFSET = 0x8000
    p = Patcher()
    rom = p.rom

    doors: Dict[int, List[bytes]] = defaultdict(list)

    for map_index in range(136):
        row = map_index // 8
        col = map_index % 8
        room_data_address = rom_info.terrain_index_13725 + 65 * row + 8 * col
        room_data = rom[room_data_address:room_data_address + 8]
        door_data_address = (room_data[5] | (room_data[6] * 256)) + BANK_4_OFFSET
        door_count = rom[door_data_address]
        door_data_address += 1
        while door_count > 0:
            door_data = rom[door_data_address:door_data_address + 5]
            doors[map_index].append(door_data)

            door_count -= 1
            door_data_address += 5

    pp(doors)


if __name__ == "__main__":
    doors_d()
