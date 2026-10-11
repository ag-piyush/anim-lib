"""Cubic Bézier helpers.

A curve is a ``(4, 2)`` array of control points ``p0, c1, c2, p3``; a batch of curves is
``(n, 4, 2)``. Everything here is vectorised over the leading axis where it can be.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def evaluate(curves: FloatArray, t: float | FloatArray) -> FloatArray:
    """Point(s) on cubic curve(s) at parameter ``t`` in [0, 1].

    ``curves`` is ``(4, 2)`` or ``(n, 4, 2)``; ``t`` is a scalar or an array broadcastable
    against the leading axis.
    """
    curves = np.asarray(curves, dtype=np.float64)
    t_arr = np.asarray(t, dtype=np.float64)[..., np.newaxis]
    s = 1.0 - t_arr
    p0, c1, c2, p3 = curves[..., 0, :], curves[..., 1, :], curves[..., 2, :], curves[..., 3, :]
    result: FloatArray = (
        s * s * s * p0 + 3 * s * s * t_arr * c1 + 3 * s * t_arr * t_arr * c2 + t_arr**3 * p3
    )
    return result


def split(curve: FloatArray, t: float) -> tuple[FloatArray, FloatArray]:
    """Split one cubic at ``t`` with de Casteljau, returning the two halves."""
    p0, c1, c2, p3 = np.asarray(curve, dtype=np.float64)
    a = p0 + t * (c1 - p0)
    b = c1 + t * (c2 - c1)
    c = c2 + t * (p3 - c2)
    d = a + t * (b - a)
    e = b + t * (c - b)
    f = d + t * (e - d)
    return np.array([p0, a, d, f]), np.array([f, e, c, p3])


def subdivide(curve: FloatArray, pieces: int) -> FloatArray:
    """Cut one cubic into ``pieces`` curves of equal parameter span, shape ``(pieces, 4, 2)``."""
    if pieces < 1:
        raise ValueError("pieces must be at least 1")
    out = np.empty((pieces, 4, 2))
    rest = np.asarray(curve, dtype=np.float64)
    for k in range(pieces, 1, -1):
        # Cutting 1/k off the front of what remains leaves k - 1 equal pieces behind it
        head, rest = split(rest, 1.0 / k)
        out[pieces - k] = head
    out[pieces - 1] = rest
    return out


def line(p0: FloatArray, p1: FloatArray) -> FloatArray:
    """A straight segment as a cubic, handles at the thirds so speed is uniform."""
    p0 = np.asarray(p0, dtype=np.float64)
    p1 = np.asarray(p1, dtype=np.float64)
    return np.array([p0, p0 + (p1 - p0) / 3, p0 + 2 * (p1 - p0) / 3, p1])


def quadratic_to_cubic(p0: FloatArray, c: FloatArray, p1: FloatArray) -> FloatArray:
    """Exact degree elevation of a quadratic Bézier."""
    p0 = np.asarray(p0, dtype=np.float64)
    c = np.asarray(c, dtype=np.float64)
    p1 = np.asarray(p1, dtype=np.float64)
    return np.array([p0, p0 + 2 * (c - p0) / 3, p1 + 2 * (c - p1) / 3, p1])


def arc(
    start_angle: float,
    sweep: float,
    radius: float = 1.0,
    center: tuple[float, float] = (0.0, 0.0),
    max_segment_angle: float = np.pi / 2,
) -> FloatArray:
    """Circular arc as cubics, each spanning at most ``max_segment_angle`` radians.

    Uses the standard handle length ``4/3 · tan(θ/4)``, whose radial error for a quarter
    circle is about 0.03% of the radius.
    """
    n = max(1, int(np.ceil(abs(sweep) / max_segment_angle - 1e-9)))
    theta = sweep / n
    k = 4.0 / 3.0 * np.tan(theta / 4.0)
    angles = start_angle + theta * np.arange(n + 1)
    cos, sin = np.cos(angles), np.sin(angles)
    points = np.stack([cos, sin], axis=1)
    tangents = np.stack([-sin, cos], axis=1)
    curves = np.empty((n, 4, 2))
    curves[:, 0] = points[:-1]
    curves[:, 1] = points[:-1] + k * tangents[:-1]
    curves[:, 2] = points[1:] - k * tangents[1:]
    curves[:, 3] = points[1:]
    result: FloatArray = curves * radius + np.asarray(center, dtype=np.float64)
    return result


def chord_lengths(curves: FloatArray) -> FloatArray:
    """Straight-line distance from start to end of each curve; a cheap stand-in for length."""
    curves = np.asarray(curves, dtype=np.float64)
    result: FloatArray = np.linalg.norm(curves[:, 3] - curves[:, 0], axis=1)
    return result


def approx_lengths(curves: FloatArray, samples: int = 8) -> FloatArray:
    """Arc length of each curve, approximated by a polyline through ``samples + 1`` points."""
    curves = np.asarray(curves, dtype=np.float64)
    ts = np.linspace(0.0, 1.0, samples + 1)
    # (samples + 1, n, 2)
    pts = evaluate(curves[np.newaxis], ts[:, np.newaxis])
    result: FloatArray = np.linalg.norm(np.diff(pts, axis=0), axis=2).sum(axis=0)
    return result
