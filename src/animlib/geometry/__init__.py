"""Paths and the operations on them: the one geometry type everything becomes."""

from animlib.geometry import bezier, shapes
from animlib.geometry.align import Morph, align, morph
from animlib.geometry.path import Path
from animlib.geometry.svg import svg_to_paths

__all__ = ["Morph", "Path", "align", "bezier", "morph", "shapes", "svg_to_paths"]
