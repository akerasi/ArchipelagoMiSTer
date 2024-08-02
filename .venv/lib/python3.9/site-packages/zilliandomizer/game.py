from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Tuple

from .logic_components.regions import RegionData
from .options import Chars, Options


@dataclass
class Game:
    options: Options
    escape_time: int
    char_order: Tuple[Chars, Chars, Chars]
    loc_name_2_pretty: Dict[str, str]
    regions: List[RegionData]
    resource_writes: Dict[int, int]

    def to_jsonable(self) -> Dict[str, Any]:
        dct = asdict(self)
        dct["regions"] = [rd.to_jsonable() for rd in self.regions]

        return dct

    @staticmethod
    def from_jsonable(game_dict: Dict[str, Any]) -> Game:
        game = Game(**game_dict)
        game.options = Options.from_jsonable(game_dict["options"])
        char_order = (game.char_order[0], game.char_order[1], game.char_order[2])
        assert len(char_order) == 3
        game.char_order = char_order
        game.regions = [RegionData.from_jsonable(region) for region in game_dict["regions"]]
        game.resource_writes = {
            int(k): v
            for k, v in game.resource_writes.items()
        }
        return game
