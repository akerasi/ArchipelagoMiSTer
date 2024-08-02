"""Define the SnesColor class."""


from .color_f import ColorF
from .math_helper import clamp


class SnesColor:
    """Represents a super NES 15-bit RGB color."""

    def __init__(self, value: int):
        self.__value = value & 0xFFFF

    @classmethod
    def from_high_and_low(cls, low: int, high: int):
        """Construct color from high and low byte values."""
        return cls((low & 0xFF) | ((high & 0xFF) << 8))

    @classmethod
    def from_rgb(cls, red: int, green: int, blue: int):
        """Construct color from 5-bit RGB values."""
        return cls(((red & 0x1F) << 0) | ((green & 0x1F) << 5) | ((blue & 0x1F) << 10))

    @classmethod
    def from_color_f(cls, color: ColorF):
        """Convert a ColorF to a SnesColor."""

        def convert_channel(value: float) -> int:
            """Convert a ColorF color channel to SnesColor color channel."""

            # First we convert the value to an 8-bit component.
            base_value = int((value * 255) + 0.5)

            # We round out the 8-bit component when converting to 5-bit.
            return clamp(base_value + 4, 0, 255) >> 3

        return cls.from_rgb(
            convert_channel(color.red),
            convert_channel(color.green),
            convert_channel(color.blue),
        )

    @property
    def value(self) -> int:
        return self.__value

    @value.setter
    def value(self, value: int):
        self.__value = value & 0x7FFF

    @property
    def proper_value(self) -> int:
        """Get the actual RGB snes color value (ignoring the highest bit)."""
        return self.value & 0x7FFF

    @proper_value.setter
    def proper_value(self, value: int):
        self.__value &= 0x8000
        self.__value |= value & 0x7FFF

    @property
    def high(self) -> int:
        return self.__value >> 8

    @high.setter
    def high(self, value: int):
        self.__value &= 0xFF00
        self.__value |= (value & 0xFF) << 8

    @property
    def low(self) -> int:
        return self.__value & 0xFF

    @low.setter
    def low(self, value: int):
        self.__value &= 0xFF00
        self.__value |= value & 0xFF

    @property
    def red(self) -> int:
        return (self.__value >> 0) & 0x1F

    @red.setter
    def red(self, value: int):
        self.__value &= ~(0x1F << 0)
        self.__value |= value & (0x1F << 0)

    @property
    def green(self) -> int:
        return (self.__value >> 5) & 0x1F

    @green.setter
    def green(self, value: int):
        self.__value &= ~(0x1F << 5)
        self.__value |= value & (0x1F << 5)

    @property
    def blue(self) -> int:
        return (self.__value >> 10) & 0x1F

    @blue.setter
    def blue(self, value: int):
        self.__value &= ~(0x1F << 10)
        self.__value |= value & (0x1F << 10)

    @property
    def inverse(self):
        return SnesColor(self.__value ^ 0x7FFF)

    def to_color_f(self) -> ColorF:
        """Convert a SnesColor to a ColorF."""

        def convert_channel(value: int) -> float:
            # We bitshift right first so that the color conversion aligns with the
            # original C# port. In it, a SnesColor was first converted to an 8 bit per
            # channel color, and then into a ColorF
            return (value << 3) / 255.0

        return ColorF(
            convert_channel(self.red),
            convert_channel(self.green),
            convert_channel(self.blue),
        )

    def __eq__(self, value) -> bool:
        return isinstance(value, SnesColor) and value.value == self.__value

    def __ne__(self, value) -> bool:
        return not self == value

    def __str__(self) -> str:
        return f"{{R:{self.red};G:{self.green};B:{self.blue}}}"

    def __repr__(self) -> str:
        return str(self)

    def __hash__(self) -> int:
        return self.__value
