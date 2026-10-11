"""Text and maths as glyph paths, through pluggable backends (Typst by default)."""

from animlib.text.typst_backend import TypstError, math, text, typst_glyphs

__all__ = ["TypstError", "math", "text", "typst_glyphs"]
