from copy import deepcopy
from typing import Dict

from zilliandomizer.low_resources.sprite_data import RoomSprites, data as sprite_data, sprite_rooms


class NPSpriteManager:
    _data: Dict[int, RoomSprites]
    """ `{ map_index: room_sprites }` """
    _saved_data: Dict[int, RoomSprites]

    def __init__(self) -> None:
        self._load()
        self.save_state()

    def _load(self) -> None:
        print("loading non-player sprites...")
        self._data = deepcopy(sprite_data)

    def get_room(self, map_index: int) -> RoomSprites:
        return deepcopy(self._data[map_index])

    def set_room(self, map_index: int, sprites: RoomSprites) -> None:
        assert len(sprites) == len(self._data[map_index]), \
            f"wrong number of sprites in room {map_index}: " \
            f"{len(sprites)} should be {len(self._data[map_index])}"
        self._data[map_index] = sprites

    def get_writes(self) -> Dict[int, int]:
        tr: Dict[int, int] = {}

        for map_index, room_address in enumerate(sprite_rooms):
            room_sprites = self._data[map_index]
            for sprite_no, sprite in enumerate(room_sprites):
                # not changing the number of sprites in each room
                sprite_address = room_address + 1 + 6 * sprite_no
                b = sprite.to_bytes()
                for i, byte in enumerate(b):
                    tr[sprite_address + i] = byte

        return tr

    def save_state(self) -> None:
        self._saved_data = deepcopy(self._data)

    def load_state(self) -> None:
        self._data = deepcopy(self._saved_data)
