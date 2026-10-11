"""Text and maths through Typst: markup in, one :class:`Path` per glyph out.

Typst is installed from a pip wheel and compiles straight to SVG, so there is no LaTeX,
dvisvgm or Pango to install. System fonts are ignored by default and Typst's bundled fonts
are used instead, so the same source renders the same on every machine.
"""

from __future__ import annotations

from collections.abc import Sequence

import typst

from animlib.geometry.path import Path
from animlib.geometry.svg import svg_to_paths

# Typst lays text out at this size; the result is then scaled to the size asked for
_LAYOUT_PT = 10.0
_PREAMBLE = (
    "#set page(width: auto, height: auto, margin: 0pt, fill: none)\n"
    f"#set text(size: {_LAYOUT_PT}pt)\n"
)


class TypstError(RuntimeError):
    """Typst could not compile the markup it was given."""


def compile_svg(
    markup: str,
    *,
    font_paths: Sequence[str] = (),
    ignore_system_fonts: bool = True,
) -> bytes:
    """Compile a fragment of Typst markup (no page set-up needed) to SVG bytes."""
    source = (_PREAMBLE + markup).encode()
    try:
        if font_paths:
            # The stubs tie font_paths to the type of the source (bytes here); str paths are
            # what the compiler actually takes
            svg = typst.compile(  # type: ignore[call-overload]
                source,
                format="svg",
                ignore_system_fonts=ignore_system_fonts,
                font_paths=list(font_paths),
            )
        else:
            svg = typst.compile(source, format="svg", ignore_system_fonts=ignore_system_fonts)
    except Exception as exc:  # typst raises a bare RuntimeError with the compiler's message
        raise TypstError(str(exc)) from exc
    if not isinstance(svg, bytes):
        raise TypstError(f"expected SVG bytes from typst, got {type(svg).__name__}")
    return svg


def typst_glyphs(
    markup: str,
    *,
    size: float = 0.5,
    font_paths: Sequence[str] = (),
    ignore_system_fonts: bool = True,
) -> list[Path]:
    """One path per glyph, scaled so the font size is ``size`` scene units and the whole
    block is centred on the origin."""
    svg = compile_svg(markup, font_paths=font_paths, ignore_system_fonts=ignore_system_fonts)
    glyphs = svg_to_paths(svg)
    if not glyphs:
        return []
    factor = size / _LAYOUT_PT
    center = Path.concat(glyphs).center()
    return [g.shift(-center[0], -center[1]).scale(factor, about=(0.0, 0.0)) for g in glyphs]


def text(markup: str, *, size: float = 0.5, font_paths: Sequence[str] = ()) -> list[Path]:
    """Typst markup such as ``"Hello *world*"``, one path per glyph."""
    return typst_glyphs(markup, size=size, font_paths=font_paths)


def math(expression: str, *, size: float = 0.5, font_paths: Sequence[str] = ()) -> list[Path]:
    """A display equation in Typst maths syntax, such as ``"e^(i pi) + 1 = 0"``."""
    return typst_glyphs(f"$ {expression} $", size=size, font_paths=font_paths)
