"""
Get options from command line, user input, or files.
"""

import argparse
import os
import io
import sys
import re

FALLBACK_CONFIG = [
    "--no-use-json",
    "--overworld",
    "--dungeon",
    "--no-link-sprite",
    "--no-sword",
    "--no-shield",
    "--mode=default",
    "--no-hud",
    "--seed=-1",
]

# Define several ways to spell out values
YES_REGEX = re.compile(r"y(?:es)?|t(?:rue)?", re.I)
NO_REGEX = re.compile(r"n(?:o)?|f(?:alse)?", re.I)
GRAYSCALE_REGEX = re.compile(r"gr[ae]y(?:scale)?", re.I)
NEGATIVE_REGEX = re.compile(r"inver(?:t|ted:se)|neg(?:ative)?", re.I)

DEFAULT_MODES = [
    "None",
    "Default",
    "Negative",
    "Grayscale",
    "Blackout",
    "Maseya",
    "Classic",
    "Dizzy",
    "Sick",
    "Puke",
]


def get_options(args=None) -> dict:
    """
    Parse command line args into a namespace object.

    Parameters
    ----------
    args : list of str, optional
        Parameter passed to `args` parameter of `parse_args` function in
        `argparse.ArgumentParser` class. The default value is `None`, which
        specifies using the program command line arguments.

    Returns
    -------
    A namesapce of the system command line argument parameters passed.
    """
    parser = argparse.ArgumentParser(
        description="Randomize palettes in The Legend of Zelda: A Link to the Past.",
        epilog="2020 Nelson Garcia",
    )
    parser.add_argument(
        "--data-dir",
        dest="data_dir",
        type=str,
        default=None,
        help="Read JSON offset files from custom directory.",
    )
    parser.add_argument(
        "-w",
        "--overworld",
        action="store_true",
        dest="randomize_overworld",
        default=True,
        help="Randomize overworld palettes. Default",
    )
    parser.add_argument(
        "-W",
        "--no-overworld",
        action="store_false",
        dest="randomize_overworld",
        help="Do not randomize overworld palettes.",
    )
    parser.add_argument(
        "-d",
        "--dungeon",
        action="store_true",
        dest="randomize_dungeon",
        default=True,
        help="Randomize overworld palettes. Default",
    )
    parser.add_argument(
        "-D",
        "--no-dungeon",
        action="store_false",
        dest="randomize_dungeon",
        help="Do not randomize overworld palettes.",
    )
    parser.add_argument(
        "-l",
        "--link-sprite",
        action="store_true",
        dest="randomize_link_sprite",
        default=False,
        help="Randomize Link sprite palette.",
    )
    parser.add_argument(
        "-L",
        "--no-link-sprite",
        action="store_false",
        dest="randomize_link_sprite",
        help="Do not randomize Link sprite palette. Default",
    )
    parser.add_argument(
        "--sword",
        action="store_true",
        dest="randomize_sword",
        default=False,
        help="Randomize sword palettes.",
    )
    parser.add_argument(
        "--no-sword",
        action="store_false",
        dest="randomize_sword",
        help="Do not randomize sword palettes. Default",
    )
    parser.add_argument(
        "--shield",
        action="store_true",
        dest="randomize_shield",
        default=False,
        help="Randomize shield palettes.",
    )
    parser.add_argument(
        "--no-shield",
        action="store_false",
        dest="randomize_shield",
        help="Do not randomize shield palettes. Default",
    )
    parser.add_argument(
        "--hud",
        action="store_true",
        dest="randomize_hud",
        default=False,
        help="Randomize HUD palettes.",
    )
    parser.add_argument(
        "--no-hud",
        action="store_false",
        dest="randomize_hud",
        help="Do not randomize HUD palettes. Default",
    )
    parser.add_argument(
        "--seed",
        type=int,
        dest="seed",
        default=-1,
        help=(
            """
Use specific seed for random generator.
Hex is supported with "0x" prefix. Default value
is -1, which specifies not using predetermined
seed.
            """
        ),
    )
    parser.add_argument(
        "--mode",
        type=str,
        dest="mode",
        default="default",
        help=(
            """
None: Makes no changes to rom.

Default: Default color mixing algorithm.
Maseya: Same as "Default".

Negative: Invert all colors.

Grayscale: Desaturate all colors.

Blackout: Set all colors to black.

Classic: Randomize palette similar to classic web API. Produces less aesthetic
    colors if that's your thing.

Dizzy: Randomize each color without logic but preserve saturation and
    lightness.

Sick: Randomize each color without logic but preserve lightness.

Puke: Randomize each color without logic.
            """
        ),
    )
    parser.add_argument("input_file", type=str, help="Input path of ROM.")
    parser.add_argument("output_file", type=str, default="", nargs="?")

    return vars(parser.parse_args(args))


def create_options_from_input(
    cin: io.TextIOBase = sys.stdin, cout: io.TextIOBase = sys.stdout
) -> dict:
    """Create options by reading from standard input and output"""

    def try_print(text: str):
        if cout:
            cout.write(text + os.linesep)

    result = dict()

    try_print("Input path to Base ROM")
    result["input_file"] = cin.readline()
    if not result["input_file"]:
        raise ValueError("No input was given.")

    try_print("Input output path to save ROM (leave empty for same as input path")
    result["output_file"] = cin.readline()
    if not result["output_file"]:
        result["output_file"] = result["input_file"]

    def parse_input_int(prompt: str, fallback: int) -> int:
        # Keep trying until we get a result.
        while True:
            # Prompt the user to give us a value.
            try_print(prompt)
            value = cin.readline()[:-1]

            # If left blank, return the default value.
            if not value:
                return fallback

            # See if the value is int-formatted
            try:
                return int(value)
            except ValueError:
                pass

            # See if the value is hexadecimal formatted.
            if value.startswith("0x"):
                try:
                    return int(value[2:], base=16)
                except ValueError:
                    pass

            try_print("Could not parse input.")

    def parse_input_bool(prompt: str, fallback: bool) -> bool:
        while True:
            try_print(prompt)
            value = cin.readline()[:-1]

            if not value:
                return fallback

            if YES_REGEX.match(value):
                return True

            if NO_REGEX.match(value):
                return False

            try_print("Could not parse input.")

    def parse_input_mode(prompt: str, fallback: str) -> str:
        while True:
            try_print(prompt)
            value = cin.readline()[:-1]

            if not value:
                return fallback

            if value in DEFAULT_MODES:
                return value

            if GRAYSCALE_REGEX.match(value):
                return "Grayscale"

            if NEGATIVE_REGEX.match(value):
                return "Negative"

            try_print("Could not parse input.")

    result["randomize_overworld"] = parse_input_bool(
        "Randomize overworld palettes? [Y]/n", True
    )
    result["randomize_dungeon"] = parse_input_bool(
        "Randomize dungeon palettes? [Y]/n", True
    )
    result["randomize_link_sprite"] = parse_input_bool(
        "Randomize Link sprite? Y/[n]", False
    )
    result["randomize_sword"] = parse_input_bool(
        "Randomize sword palettes? Y/[n]", False
    )
    result["randomize_shield"] = parse_input_bool(
        "Randomize shield palettes? y/[N]", False
    )
    result["randomize_hud"] = parse_input_bool("Randomize HUD palettes? Y/[n]", False)
    result["seed"] = parse_input_int(
        "Custom seed (leave blank for system default):", -1
    )
    result["mode"] = parse_input_mode(
        "Enter randomizer mode (none, [default], blackout, negative, grayscale, puke",
        "default",
    )

    try_print("Enter custom directory to offset files (leave blank to use defaults):")
    result["data_dir"] = cin.readline()[:-1]

    return result


def get_options_from_anywhere(args) -> dict:
    """Get options from command line args, or user if no args were given."""
    # If the user passed in no args, it's possible this may represent a system call.
    if not args:
        # So let's verify if this is a system call with no command line parameters.
        if len(sys.argv) == 1:
            # If it is, then let's get the options from the user.
            return create_options_from_input()

    return get_options(args)
