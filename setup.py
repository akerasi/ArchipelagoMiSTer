import base64
import datetime
import os
import platform
import shutil
import sys
import sysconfig
import typing
import warnings
import zipfile
import urllib.request
import io
import json
import threading
import subprocess

from collections.abc import Iterable
from hashlib import sha3_512
from pathlib import Path

from worlds.LauncherComponents import components, icon_paths
from Utils import version_tuple, is_windows, is_linux
from Cython.Build import cythonize


# On  Python < 3.10 LogicMixin is not currently supported.
non_apworlds: set = {
    "A Link to the Past",
    "Adventure",
    "Archipelago",
    "Final Fantasy",
    "Lufia II Ancient Cave",
    "Meritous",
    "Ocarina of Time",
    "Super Mario 64",
}

build_platform = sysconfig.get_platform()
arch_folder = "exe.{platform}-{version}".format(platform=build_platform,
                                                version=sysconfig.get_python_version())
buildfolder = Path("build", arch_folder)
build_arch = build_platform.split('-')[-1] if '-' in build_platform else platform.machine()


# see Launcher.py on how to add scripts to setup.py
def resolve_icon(icon_name: str):
    base_path = icon_paths[icon_name]
    if is_windows:
        path, extension = os.path.splitext(base_path)
        ico_file = path + ".ico"
        assert os.path.exists(ico_file), f"ico counterpart of {base_path} should exist."
        return ico_file
    else:
        return base_path


extra_data = ["LICENSE", "data", "EnemizerCLI"]
extra_libs = ["libssl.so", "libcrypto.so"] if is_linux else []


def remove_sprites_from_folder(folder):
    for file in os.listdir(folder):
        if file != ".gitignore":
            os.remove(folder / file)


def _threaded_hash(filepath):
    hasher = sha3_512()
    hasher.update(open(filepath, "rb").read())
    return base64.b85encode(hasher.digest()).decode()