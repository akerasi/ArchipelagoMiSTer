import abc
from dataclasses import dataclass
from typing import List


class EventFromGame(abc.ABC):
    ...


class DeathEventFromGame(EventFromGame):
    pass


@dataclass
class MapEventFromGame(EventFromGame):
    map_index: int


@dataclass
class AcquireLocationEventFromGame(EventFromGame):
    """ 0 for main computer """
    id: int


class WinEventFromGame(EventFromGame):
    pass


@dataclass
class DoorEventFromGame(EventFromGame):
    """ These are the doors I've opened. """
    doors: bytes


class EventToGame(abc.ABC):
    ...


@dataclass
class ItemEventToGame(EventToGame):
    ids: List[int]


class DeathEventToGame(EventToGame):
    pass


@dataclass
class DoorEventToGame(EventToGame):
    """ At least these doors should be open. """
    doors: bytes
