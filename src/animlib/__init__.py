"""anim-lib: programmatic, explanatory animations in the spirit of manim.

Phase 0 surface: build paths, morph between them, render frames with Skia and encode them
with PyAV. The scene and timeline API arrives in phase 1; see docs/architecture.md.
"""

from importlib.metadata import PackageNotFoundError, version

from animlib.core import Color, easing
from animlib.geometry import Morph, Path, align, morph, shapes
from animlib.output import VideoWriter, save_png
from animlib.render import Camera, DrawItem, SkiaRenderer, Style
from animlib.text import math, text

try:
    __version__ = version("anim-lib")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0+unknown"

__all__ = [
    "Camera",
    "Color",
    "DrawItem",
    "Morph",
    "Path",
    "SkiaRenderer",
    "Style",
    "VideoWriter",
    "__version__",
    "align",
    "easing",
    "math",
    "morph",
    "save_png",
    "shapes",
    "text",
]
