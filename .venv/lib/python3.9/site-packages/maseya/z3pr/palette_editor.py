"""Define the PaletteEditor class."""

from typing import Callable, Iterable, List, Mapping

from .snes_color import SnesColor
from .color_f import ColorF


class PaletteEditor:
    """Stores a collection of palette data from a ROM."""

    def __init__(self, rom: bytearray, offsets: List[int]):
        def raw(offset: int) -> SnesColor:
            """Get simple palette color from rom offset."""
            return SnesColor.from_high_and_low(rom[offset], rom[offset + 1])

        def oam(offset: int) -> SnesColor:
            """Get OAM palette color."""
            return SnesColor.from_rgb(
                rom[offset] & 0x1F, rom[offset + 1] & 0x1F, rom[offset + 4] & 0x1F
            )

        def get_color(offset: int) -> SnesColor:
            """Get an OAM color if offset is negative, or raw color otherwise."""
            return raw(offset) if offset >= 0 else oam(-offset)

        # Store palette data as a dictionary of the offsets and their ColorF values.
        self.__items = {offset: get_color(offset).to_color_f() for offset in offsets}

    def blend(
        self,
        blend: Callable[[ColorF, ColorF], ColorF],
        color_generator: Iterable[ColorF],
    ):
        """Blend palette data using blend function and color generator."""
        # Get base color from passed funcion.
        base_color = next(color_generator)

        # Blend each color in the palette editor.
        for offset in self.__items.keys():
            self.__items[offset] = blend(self.__items[offset], base_color)

    def get_color_groups(self) -> Mapping[ColorF, List[int]]:
        result = dict()
        for offset, color in self.__items.items():
            offsets = result.get(color, None)
            if not offsets:
                result[color] = [offset]
            else:
                offsets.append(offset)
        return result

    def blend_by_color(
        self,
        blend: Callable[[ColorF, ColorF], ColorF],
        color_generator: Iterable[ColorF],
    ):
        for color, offsets in self.get_color_groups().items():
            new_color = blend(color, next(color_generator))
            for offset in offsets:
                self.__items[offset] = new_color

    def write_to_rom(self, rom: bytearray):
        """Write palette data to rom."""

        def raw(offset: int, color: SnesColor):
            """Write raw palette color."""
            rom[offset + 0] = color.low
            rom[offset + 1] = color.high

        def oam(offset: int, color: SnesColor):
            """Write OAM palette color."""
            # OAM palettes store red, green, and blue color components with
            # 0x20, 0x40, and 0x80 bits, respectively.
            rom[offset + 0] = color.red | 0x20
            rom[offset + 1] = color.green | 0x40
            rom[offset + 3] = color.green | 0x40
            rom[offset + 4] = color.blue | 0x80

        def write_color(offset: int, color: SnesColor):
            """Write OAM color if offset is negative, otherwise normal color."""
            if offset >= 0:
                raw(offset, color)
            else:
                oam(-offset, color)

        # Write each color in the palette editor back to the rom.
        for offset, color in self.__items.items():
            write_color(offset, SnesColor.from_color_f(color))
