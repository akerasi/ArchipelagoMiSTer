"""
Application entry point.
"""

from .palette_randomizer import randomize_from_options
from .options import get_options

randomize_from_options(get_options())
