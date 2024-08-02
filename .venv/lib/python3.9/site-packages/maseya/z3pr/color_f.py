"""
Define the ColorF class, which represents a color as 3 floats.

These algorithms come from
https://en.wikipedia.org/wiki/HSL_and_HSV#Color_conversion_formulae
"""

from typing import Tuple
from math import fmod

from .math_helper import clamp

LUMA_RED_WEIGHT = 0.299
LUMA_GREEN_WEIGHT = 0.587
LUMA_BLUE_WEIGHT = 0.114


class ColorF:  # pylint: disable=too-many-public-methods
    """An RGB color where each RGB component is between [0, 1]."""

    def __init__(self, red: float, green: float, blue: float):
        self.__red = red
        self.__green = green
        self.__blue = blue

    @classmethod
    def from_cmy(cls, cyan: float, magenta: float, yellow: float):
        return cls(1 - cyan, 1 - magenta, 1 - yellow)

    @property
    def red(self) -> float:
        return self.__red

    @property
    def green(self) -> float:
        return self.__green

    @property
    def blue(self) -> float:
        return self.__blue

    @property
    def cyan(self) -> float:
        return 1 - self.__red

    @property
    def magenta(self) -> float:
        return 1 - self.__green

    @property
    def yellow(self) -> float:
        return 1 - self.__blue

    @property
    def max_of_rgb(self) -> float:
        return max([self.__red, self.__green, self.__blue])

    @property
    def min_of_rgb(self) -> float:
        return min([self.__red, self.__green, self.__blue])

    @property
    def chroma(self) -> float:
        return self.max_of_rgb - self.min_of_rgb

    @property
    def luma(self) -> float:
        return (
            (LUMA_RED_WEIGHT * self.__red)
            + (LUMA_GREEN_WEIGHT * self.__green)
            + (LUMA_BLUE_WEIGHT * self.__blue)
        )

    @property
    def lightness(self) -> float:
        return (self.max_of_rgb + self.min_of_rgb) / 2

    @property
    def saturation(self) -> float:
        if self.lightness == 0 or self.lightness == 1:
            return 0
        return clamp(self.chroma / (1 - abs((2 * self.lightness) - 1)), 0, 1)

    @property
    def hue(self) -> float:
        # Technically, NaN should be returned, but returning 0 helps performance.
        if self.chroma == 0:
            return 0

        max_rgb = self.max_of_rgb
        if max_rgb == self.__red:
            hue = (self.__green - self.__blue) / self.chroma
            # Make sure hue is fmodded between 0 and 6.
            if hue < 0:
                hue += 6
        elif max_rgb == self.__green:
            hue = ((self.__blue - self.__red) / self.chroma) + 2
        else:
            hue = ((self.__red - self.__green) / self.chroma) + 4

        return hue / 6.0

    @property
    def hue_degrees(self) -> float:
        return self.hue * 360

    def __eq__(self, value) -> bool:
        return (
            isinstance(value, ColorF)
            and self.__red == value.red
            and self.__green == value.green
            and self.__blue == value.blue
        )

    def __ne__(self, value) -> bool:
        return not self == value

    @property
    def inverse(self):
        return ColorF(self.cyan, self.magenta, self.yellow)

    @staticmethod
    def get_base_rgb(  # pylint: disable=too-many-return-statements
        hue: float, chroma: float
    ) -> Tuple[float, float, float]:
        """Get base RGB components, ignoring lightness or luma."""
        if chroma == 0:
            return 0, 0, 0

        hue = fmod(1 + fmod(hue, 1), 1)
        hue *= 6

        secondary = chroma * (1 - abs((hue % 2) - 1))
        if hue <= 1:
            return chroma, secondary, 0
        if hue <= 2:
            return secondary, chroma, 0
        if hue <= 3:
            return 0, chroma, secondary
        if hue <= 4:
            return 0, secondary, chroma
        if hue <= 5:
            return secondary, 0, chroma
        return chroma, 0, secondary

    @classmethod
    def from_hcy(cls, hue: float, chroma: float, luma: float):
        chroma = clamp(chroma, 0, 1)
        luma = clamp(luma, 0, 1)
        red, green, blue = cls.get_base_rgb(hue, chroma)

        luma_red = red * LUMA_RED_WEIGHT
        luma_green = green * LUMA_GREEN_WEIGHT
        luma_blue = blue * LUMA_BLUE_WEIGHT
        base_luma = luma_red + luma_green + luma_blue

        base_rgb = clamp(luma - base_luma, 0, 1)
        return cls(base_rgb + red, base_rgb + green, base_rgb + blue)

    @classmethod
    def from_hsl(cls, hue: float, saturation: float, lightness: float):
        saturation = clamp(saturation, 0, 1)
        lightness = clamp(lightness, 0, 1)

        chroma = (1 - abs((2 * lightness) - 1)) * saturation
        red, green, blue = cls.get_base_rgb(hue, chroma)
        match = lightness - (chroma / 2)

        return cls(match + red, match + green, match + blue)

    @classmethod
    def hue_blend(cls, left, right):
        return cls.from_hcy(right.hue, left.chroma, left.luma)

    @classmethod
    def chroma_blend(cls, left, right):
        return cls.from_hcy(left.hue, right.chroma, left.luma)

    @classmethod
    def luma_blend(cls, left, right):
        return cls.from_hcy(left.hue, left.chroma, right.luma)

    @property
    def grayscale(self):
        return self.from_hcy(0, 0, self.luma)

    def __hash__(self) -> int:
        return hash((self.red, self.green, self.blue))

    def __str__(self) -> str:
        return f"{{R:{self.red};G:{self.green};B:{self.blue}}}"

    def __repr__(self) -> str:
        return str(self)
