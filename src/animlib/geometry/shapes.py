"""Basic shapes, each returned as a :class:`~animlib.geometry.path.Path` centred on the origin
unless a centre is given. Closed shapes all run counter-clockwise, so two of them morph into
each other without turning inside out."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike

from animlib.geometry import bezier
from animlib.geometry.path import FloatArray, Path

TAU = 2 * np.pi


def circle(radius: float = 1.0, center: ArrayLike = (0.0, 0.0)) -> Path:
    curves = bezier.arc(0.0, TAU, radius, (0.0, 0.0))
    return Path.from_subpaths([(curves, True)]).shift(*np.asarray(center, dtype=np.float64))


def ellipse(width: float = 2.0, height: float = 1.0, center: ArrayLike = (0.0, 0.0)) -> Path:
    return (
        circle(1.0)
        .scale((width / 2, height / 2), about=(0.0, 0.0))
        .shift(*np.asarray(center, dtype=np.float64))
    )


def arc(
    radius: float = 1.0,
    start_angle: float = 0.0,
    sweep: float = np.pi / 2,
    center: ArrayLike = (0.0, 0.0),
) -> Path:
    c = np.asarray(center, dtype=np.float64)
    curves = bezier.arc(start_angle, sweep, radius, (float(c[0]), float(c[1])))
    return Path.from_subpaths([(curves, False)])


def line(start: ArrayLike, end: ArrayLike) -> Path:
    return Path.from_subpaths(
        [(bezier.line(np.asarray(start), np.asarray(end))[np.newaxis], False)]
    )


def regular_polygon(n: int, radius: float = 1.0, start_angle: float = 0.0) -> Path:
    """``n`` corners on a circle of ``radius``, the first at ``start_angle``."""
    if n < 3:
        raise ValueError("a polygon needs at least 3 corners")
    angles = start_angle + TAU * np.arange(n) / n
    points = radius * np.stack([np.cos(angles), np.sin(angles)], axis=1)
    return Path.polyline(points, closed=True)


def rectangle(width: float = 2.0, height: float = 1.0, corner_radius: float = 0.0) -> Path:
    """Axis-aligned rectangle; ``corner_radius`` rounds every corner with a quarter circle."""
    w, h = width / 2, height / 2
    r = float(np.clip(corner_radius, 0.0, min(w, h)))
    if r == 0.0:
        # Counter-clockwise from the top-right corner
        return Path.polyline([(w, h), (-w, h), (-w, -h), (w, -h)], closed=True)
    corners = [(w - r, h - r), (-w + r, h - r), (-w + r, -h + r), (w - r, -h + r)]
    curves: list[FloatArray] = []
    for i, (cx, cy) in enumerate(corners):
        quarter = bezier.arc(i * np.pi / 2, np.pi / 2, r, (cx, cy))
        if curves:
            curves.append(bezier.line(curves[-1][3], quarter[0, 0]))
        curves.extend(quarter)
    curves.append(bezier.line(curves[-1][3], curves[0][0]))
    return Path.from_subpaths([(np.array(curves), True)])


def square(side: float = 2.0, corner_radius: float = 0.0) -> Path:
    return rectangle(side, side, corner_radius)


def star(points: int = 5, outer_radius: float = 1.0, inner_radius: float = 0.4) -> Path:
    angles = np.pi / 2 + np.pi * np.arange(2 * points) / points
    radii = np.where(np.arange(2 * points) % 2 == 0, outer_radius, inner_radius)
    pts = radii[:, np.newaxis] * np.stack([np.cos(angles), np.sin(angles)], axis=1)
    return Path.polyline(pts, closed=True)
