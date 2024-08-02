from copy import deepcopy
from typing import Dict, List

from zilliandomizer.low_resources import rom_info
from zilliandomizer.low_resources.terrain_compressor import TerrainCompressor
from zilliandomizer.low_resources.terrain_mods import terrain_mods


class TerrainModifier:
    """
    This class holds the terrain data and lets us change it one room at a time.

    The original game does not have optimal compression for the terrain data.
    With better compression, it can be stored in 77 fewer bytes.
    This gives some room to make changes to the terrain.
    """

    _map_indexes: List[int]
    """ rooms that aren't hallways """
    _rooms: Dict[int, List[int]]
    """ map index: recompressed bytes (including 0 on end) """
    _size: int
    """ total """

    # need to be able to save state this class, to try generating things multiple times
    _saved_rooms: Dict[int, List[int]]
    _saved_size: int

    def __init__(self) -> None:
        self.load()
        self.save_state()  # make sure there's always something to load

    def load(self) -> None:
        self._rooms = deepcopy(terrain_mods)
        self._map_indexes = [map_index for map_index in self._rooms]
        self._size = sum(len(room) for room in self._rooms.values())

        original_size = rom_info.terrain_end_120da - rom_info.terrain_begin_10ef0
        assert original_size - self._size == 77, f"original terrain size: {original_size}  recompressed: {self._size}"
        # print(f"average compressed size: {self._size / len(self._map_indexes)}")
        # print(f"average original size: {original_size / len(self._map_indexes)}")
        # print(f"room count: {len(self._map_indexes)}")

    def get_writes(self) -> Dict[int, int]:
        tr: Dict[int, int] = {}

        terrain_cursor = rom_info.terrain_begin_10ef0

        for map_index in self._map_indexes:
            row = map_index // 8
            col = map_index % 8
            index_address = rom_info.terrain_index_13725 + row * 65 + 1 + col * 8
            banked_address = terrain_cursor - TerrainCompressor.BANK_OFFSET
            tr[index_address] = banked_address & 0xff
            tr[index_address + 1] = banked_address >> 8
            for byte in self._rooms[map_index]:
                tr[terrain_cursor] = byte
                terrain_cursor += 1

        assert terrain_cursor <= rom_info.terrain_end_120da

        return tr

    def get_space(self) -> int:
        """ return number of bytes from limit (negative if over limit) """
        return (rom_info.terrain_end_120da - rom_info.terrain_begin_10ef0) - self._size

    def get_room(self, map_index: int) -> List[int]:
        """ compressed """
        return self._rooms[map_index][:]

    def set_room(self, map_index: int, data: List[int]) -> None:
        """ compressed, return number of bytes from limit (negative if over limit) """
        self._size -= len(self._rooms[map_index])
        self._size += len(data)
        self._rooms[map_index] = data[:]  # copy to make sure it doesn't get modified after setting

    def save_state(self) -> None:
        self._saved_rooms = deepcopy(self._rooms)
        self._saved_size = self._size

    def load_state(self) -> None:
        self._rooms = deepcopy(self._saved_rooms)
        self._size = self._saved_size
