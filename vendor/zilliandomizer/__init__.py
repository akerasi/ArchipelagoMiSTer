from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("zilliandomizer")
except PackageNotFoundError:
    # package is not installed
    pass
