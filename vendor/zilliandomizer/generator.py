import os

from zilliandomizer.system import System
from zilliandomizer.ver import version_hash, date
from zilliandomizer.options import Options, ID
from zilliandomizer.options.parsing import parse_options
from zilliandomizer.logger import Logger

some_options = Options(item_counts={
    ID.card: 50,
    ID.bread: 35,
    ID.opa: 26,
    ID.gun: 9,
    ID.floppy: 8,
    ID.scope: 4,
    ID.red: 2
}, jump_levels="balanced", gun_levels="balanced", opas_per_level=2, max_level=8, tutorial=False,
    skill=2, start_char="JJ", floppy_req=5)
""" default options if no options.yaml """


def generate(seed: int) -> None:
    seed_str = f"{seed:016x}"
    print(f"generating seed {seed_str}")
    logger = Logger()
    logger.spoil_stdout = False
    system = System(logger)
    p = system.make_patcher()
    options: Options = some_options
    options_file = p.rom_path + os.sep + "options.yaml"
    if os.path.exists(options_file):
        print(f"found options file: {options_file}")
        with open(options_file) as file:
            options = parse_options(file.read())
    else:
        print("no options file found, using default")
    logger.spoil(str(options))
    logger.spoil(f"seed {seed_str}")
    logger.spoil(f"zilliandomizer version: {version_hash} {date}")

    system.set_options(options)
    system.seed(seed)
    system.make_map()
    r = system.make_randomizer()

    r.roll()

    system.post_fill()

    game = system.get_game()

    p.write_locations(game.regions, options.start_char)
    p.all_fixes_and_options(game)

    # testing
    # from typing import Dict, Tuple
    # from random import randrange
    # p.set_external_item_interface(options.start_char, options.max_level)
    # empties: Dict[str, Tuple[str, str]] = {}
    # letter = 0
    # for loc in r.locations:
    #     item = r.locations[loc].item
    #     if item and item.id == ID.empty:
    #         name = f"{chr(ord('A') + letter)}{chr(ord('a') + randrange(26))}q"
    #         empties[loc] = ("", name)
    #         letter = (letter + 1) % 26
    #         print(f"{loc}: {name}")
    # print(f"empty count: {len(empties)}  unique: {len(set(empties.values()))}  "
    #       f"uppered: {len(set(n.upper() for _, n in empties.values()))}")
    # p.set_multiworld_items(empties)
    # p.set_rom_to_ram_data("𝄞𝄵𝄫𝅘𝅥𝅮𝆓𝆑𝆑𝄐𝄻𝄡𝄆𝄇𝆲𝄶𝄂".encode())  # "MESSAGE TO RAM".encode())

    filename = f"zilliandomizer-{seed_str}.sms"
    p.write(filename)
    # TODO: abstract out the spoiler writer (handling directory in a better way)
    spoiler_file_name = p.rom_path + os.sep + f"spoiler-{seed_str}.txt"
    with open(spoiler_file_name, "wt") as file:
        for line in logger.spoiler_lines:
            file.write(line + "\n")
    print(f"generated: {filename}")
    print(f"spoiler: {spoiler_file_name}")
