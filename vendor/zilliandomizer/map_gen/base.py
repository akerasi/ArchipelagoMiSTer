from dataclasses import dataclass
from typing import AbstractSet, Mapping, Union

from .base_maker import BaseMaker, Node
from .door_manager import DoorManager


@dataclass
class Base:
    red: BaseMaker
    paperclip: BaseMaker
    dm: DoorManager
    pc_splits: Mapping[Node, Node]
    pudding_cans: Union[AbstractSet[int], None] = None
    """ which map indexes have a can in the pudding """
