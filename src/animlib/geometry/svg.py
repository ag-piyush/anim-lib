"""SVG to :class:`~animlib.geometry.path.Path`, via ``svgelements``.

``svgelements`` resolves ``<use>``, nested transforms and basic shapes for us; this module
turns what it yields into cubic subpaths, flips y so it points up, and keeps one path per
drawn element so that, for example, each glyph of a line of text stays addressable.
"""

from __future__ import annotations

import io
from collections.abc import Iterator

import numpy as np
import svgelements as se

from animlib.geometry import bezier
from animlib.geometry.path import FloatArray, Path


def _xy(point: se.Point) -> FloatArray:
    return np.array([float(point.x), float(point.y)])


def _segments_to_subpaths(path: se.Path) -> Iterator[tuple[FloatArray, bool]]:
    curves: list[FloatArray] = []
    closed = False
    for seg in path.segments():
        if isinstance(seg, se.Move):
            if curves:
                yield np.array(curves), closed
            curves, closed = [], False
        elif isinstance(seg, se.Close):
            if curves and not np.allclose(curves[-1][3], curves[0][0]):
                curves.append(bezier.line(curves[-1][3], curves[0][0]))
            if curves:
                yield np.array(curves), True
            curves, closed = [], False
        elif isinstance(seg, se.Line):
            curves.append(bezier.line(_xy(seg.start), _xy(seg.end)))
        elif isinstance(seg, se.QuadraticBezier):
            curves.append(bezier.quadratic_to_cubic(_xy(seg.start), _xy(seg.control), _xy(seg.end)))
        elif isinstance(seg, se.CubicBezier):
            curves.append(
                np.array([_xy(seg.start), _xy(seg.control1), _xy(seg.control2), _xy(seg.end)])
            )
        elif isinstance(seg, se.Arc):
            for cubic in seg.as_cubic_curves():
                curves.append(
                    np.array(
                        [_xy(cubic.start), _xy(cubic.control1), _xy(cubic.control2), _xy(cubic.end)]
                    )
                )
    if curves:
        yield np.array(curves), closed


def element_to_path(element: se.Shape) -> Path:
    """One SVG shape (already carrying its transforms) as a Path, still in SVG coordinates."""
    shape = element if isinstance(element, se.Path) else se.Path(element)
    shape = shape * shape.transform if not shape.transform.is_identity() else shape
    if not isinstance(shape, se.Path):
        shape = se.Path(shape)
    return Path.from_subpaths(_segments_to_subpaths(shape))


def svg_to_paths(svg: bytes | str, *, skip_background: bool = True) -> list[Path]:
    """Every visible shape in an SVG document, in document order, with y flipped to point up.

    ``skip_background`` drops a leading full-page rectangle such as a page fill.
    """
    data = svg.encode() if isinstance(svg, str) else svg
    document = se.SVG.parse(io.BytesIO(data), reify=True)
    paths: list[Path] = []
    for element in document.elements():
        if not isinstance(element, se.Shape) or isinstance(element, se.SVG):
            continue
        if element.values.get("visibility") == "hidden":
            continue
        path = element_to_path(element)
        if path.is_empty():
            continue
        paths.append(path)

    # svgelements maps the viewBox onto the document's physical size in CSS pixels (so a
    # width given in pt is scaled by 96/72). Undo that, so results are in viewBox units: the
    # units the SVG was authored in, which for Typst output are points.
    vb = document.viewbox
    to_user = np.eye(3)
    if vb is not None and document.width and document.height:
        to_user = np.array(
            [
                [vb.width / document.width, 0.0, vb.x],
                [0.0, vb.height / document.height, vb.y],
                [0.0, 0.0, 1.0],
            ]
        )
    paths = [p.apply_matrix(to_user) for p in paths]

    if skip_background and paths and vb is not None:
        lo, hi = paths[0].bounds()
        page = np.array([vb.x, vb.y]), np.array([vb.x + vb.width, vb.y + vb.height])
        if np.allclose(lo, page[0], atol=1e-6) and np.allclose(hi, page[1], atol=1e-6):
            paths = paths[1:]
    flip = np.array([[1.0, 0.0], [0.0, -1.0]])
    return [p.apply_matrix(flip) for p in paths]
