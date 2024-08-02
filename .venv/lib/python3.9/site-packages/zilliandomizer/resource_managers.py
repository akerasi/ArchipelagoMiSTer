from dataclasses import dataclass, field
from typing import Dict, Tuple

from zilliandomizer.np_sprite_manager import NPSpriteManager
from zilliandomizer.options import Chars
from zilliandomizer.room_gen.aem import AlarmEntranceManager
from zilliandomizer.terrain_modifier import TerrainModifier


@dataclass
class ResourceManagers:
    """ holds the result of various randomizations in the seed """
    tm: TerrainModifier = field(default_factory=TerrainModifier)
    sm: NPSpriteManager = field(default_factory=NPSpriteManager)
    aem: AlarmEntranceManager = field(default_factory=AlarmEntranceManager)
    escape_time: int = 300
    char_order: Tuple[Chars, Chars, Chars] = ("JJ", "Apple", "Champ")
    """ `start_char, captured_1, captured_2` """

    def get_writes(self) -> Dict[int, int]:
        return {
            **self.tm.get_writes(),
            **self.sm.get_writes(),
            **self.aem.get_writes()
        }
