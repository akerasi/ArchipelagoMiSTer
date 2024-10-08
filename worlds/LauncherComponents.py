import bisect
import logging
import pathlib
import weakref
from enum import Enum, auto
from typing import Optional, Callable, List, Iterable, Tuple

from Utils import local_path, open_filename


class Type(Enum):
    TOOL = auto()
    MISC = auto()
    CLIENT = auto()
    ADJUSTER = auto()
    FUNC = auto()  # do not use anymore
    HIDDEN = auto()


class Component:
    display_name: str
    type: Type
    script_name: Optional[str]
    frozen_name: Optional[str]
    icon: str  # just the name, no suffix
    cli: bool
    func: Optional[Callable]
    file_identifier: Optional[Callable[[str], bool]]

    def __init__(self, display_name: str, script_name: Optional[str] = None, frozen_name: Optional[str] = None,
                 cli: bool = False, icon: str = 'icon', component_type: Optional[Type] = None,
                 func: Optional[Callable] = None, file_identifier: Optional[Callable[[str], bool]] = None):
        self.display_name = display_name
        self.script_name = script_name
        self.frozen_name = frozen_name or f'Archipelago{script_name}' if script_name else None
        self.icon = icon
        self.cli = cli
        if component_type == Type.FUNC:
            from Utils import deprecate
            deprecate(f"Launcher Component {self.display_name} is using Type.FUNC Type, which is pending removal.")
            component_type = Type.MISC

        self.type = component_type or (
            Type.CLIENT if "Client" in display_name else
            Type.ADJUSTER if "Adjuster" in display_name else Type.MISC)
        self.func = func
        self.file_identifier = file_identifier

    def handles_file(self, path: str):
        return self.file_identifier(path) if self.file_identifier else False

    def __repr__(self):
        return f"{self.__class__.__name__}({self.display_name})"


processes = weakref.WeakSet()


def launch_subprocess(func: Callable, name: str = None):
    global processes
    import multiprocessing
    process = multiprocessing.Process(target=func, name=name)
    process.start()
    processes.add(process)


class SuffixIdentifier:
    suffixes: Iterable[str]

    def __init__(self, *args: str):
        self.suffixes = args

    def __call__(self, path: str) -> bool:
        if isinstance(path, str):
            for suffix in self.suffixes:
                if path.endswith(suffix):
                    return True
        return False


def launch_textclient():
    import CommonClient
    launch_subprocess(CommonClient.run_as_textclient, name="TextClient")


def _install_apworld(apworld_src: str = "") -> Optional[Tuple[pathlib.Path, pathlib.Path]]:
    if not apworld_src:
        apworld_src = open_filename('Select APWorld file to install', (('APWorld', ('.apworld',)),))
        if not apworld_src:
            # user closed menu
            return

    if not apworld_src.endswith(".apworld"):
        raise Exception(f"Wrong file format, looking for .apworld. File identified: {apworld_src}")

    apworld_path = pathlib.Path(apworld_src)

    module_name = pathlib.Path(apworld_path.name).stem
    try:
        import zipfile
        zipfile.ZipFile(apworld_path).open(module_name + "/__init__.py")
    except ValueError as e:
        raise Exception("Archive appears invalid or damaged.") from e
    except KeyError as e:
        raise Exception("Archive appears to not be an apworld. (missing __init__.py)") from e

    import worlds
    if worlds.user_folder is None:
        raise Exception("Custom Worlds directory appears to not be writable.")
    for world_source in worlds.world_sources:
        if apworld_path.samefile(world_source.resolved_path):
            # Note that this doesn't check if the same world is already installed.
            # It only checks if the user is trying to install the apworld file
            # that comes from the installation location (worlds or custom_worlds)
            raise Exception(f"APWorld is already installed at {world_source.resolved_path}.")

    # TODO: run generic test suite over the apworld.
    # TODO: have some kind of version system to tell from metadata if the apworld should be compatible.

    target = pathlib.Path(worlds.user_folder) / apworld_path.name
    import shutil
    shutil.copyfile(apworld_path, target)

    # If a module with this name is already loaded, then we can't load it now.
    # TODO: We need to be able to unload a world module,
    # so the user can update a world without restarting the application.
    found_already_loaded = False
    for loaded_world in worlds.world_sources:
        loaded_name = pathlib.Path(loaded_world.path).stem
        if module_name == loaded_name:
            found_already_loaded = True
            break
    if found_already_loaded:
        raise Exception(f"Installed APWorld successfully, but '{module_name}' is already loaded,\n"
                        "so a Launcher restart is required to use the new installation.")
    world_source = worlds.WorldSource(str(target), is_zip=True)
    bisect.insort(worlds.world_sources, world_source)
    world_source.load()

    return apworld_path, target


def install_apworld(apworld_path: str = "") -> None:
    try:
        res = _install_apworld(apworld_path)
        if res is None:
            logging.info("Aborting APWorld installation.")
            return
        source, target = res
    except Exception as e:
        import Utils
        Utils.messagebox(e.__class__.__name__, str(e), error=True)
        logging.exception(e)
    else:
        import Utils
        logging.info(f"Installed APWorld successfully, copied {source} to {target}.")
        Utils.messagebox("Install complete.", f"Installed APWorld from {source}.")


components: List[Component] = [

    Component('Generate', 'Generate', cli=True),
    Component('Patch', 'Patch', cli=True),
    Component("Install APWorld", func=install_apworld, file_identifier=SuffixIdentifier(".apworld")),
    Component('LttP Adjuster', 'LttPAdjuster'),
    Component('OoT Adjuster', 'OoTAdjuster')
]


icon_paths = {
    'icon': local_path('data', 'icon.png'),
    'mcicon': local_path('data', 'mcicon.png'),
    'discord': local_path('data', 'discord-mark-blue.png'),
}
