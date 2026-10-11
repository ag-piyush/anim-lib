from pathlib import Path as FilePath

import numpy as np
import pytest

from animlib import Path, math, text
from animlib.geometry import svg_to_paths
from animlib.text import TypstError


def test_one_path_per_glyph() -> None:
    glyphs = text("Hi")
    assert len(glyphs) == 2
    # "i" is a stem and a dot: one glyph, two subpaths
    assert glyphs[1].num_subpaths == 2


def test_text_is_centred_and_sized() -> None:
    glyphs = text("Hello", size=1.0)
    whole = Path.concat(glyphs)
    assert np.allclose(whole.center(), [0, 0], atol=1e-9)
    # A capital letter is roughly 0.6 to 0.75 of the font size tall
    assert 0.5 < glyphs[0].height < 0.8


def test_size_scales_linearly() -> None:
    small = Path.concat(text("Ag", size=0.5))
    large = Path.concat(text("Ag", size=1.5))
    assert large.width == pytest.approx(3 * small.width)
    assert large.height == pytest.approx(3 * small.height)


def test_text_reads_left_to_right() -> None:
    xs = [g.center()[0] for g in text("abc")]
    assert xs == sorted(xs)


def test_superscript_sits_higher() -> None:
    base, exponent = math("x^2")
    assert exponent.center()[1] > base.center()[1]


def test_same_source_renders_the_same() -> None:
    a = Path.concat(math("integral_0^1 x dif x"))
    b = Path.concat(math("integral_0^1 x dif x"))
    assert np.array_equal(a.curves, b.curves)


def test_extra_font_paths_are_accepted(tmp_path: FilePath) -> None:
    assert len(text("Hi", font_paths=[str(tmp_path)])) == 2


def test_compile_errors_are_reported() -> None:
    with pytest.raises(TypstError):
        text("#let x = ")


def test_svg_flips_y_and_skips_page_background() -> None:
    svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        b'<rect x="0" y="0" width="10" height="10" fill="white"/>'
        b'<rect x="1" y="1" width="2" height="3"/></svg>'
    )
    (path,) = svg_to_paths(svg)
    lo, hi = path.bounds()
    assert np.allclose(lo, [1, -4])
    assert np.allclose(hi, [3, -1])
