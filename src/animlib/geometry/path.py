"""The one geometry type everything becomes: a set of subpaths made of cubic Béziers.

Shapes, SVG files, text and maths all end up as a :class:`Path`, which is what lets any of
them morph into any other.

Layout
------
``curves``       ``(n, 4, 2)`` float64, control points of every cubic in drawing order.
``subpath_ids``  ``(n,)`` int, which subpath each curve belongs to; non-decreasing, from 0.
``closed``       ``(k,)`` bool, whether subpath ``i`` closes back on its start.

Coordinates are scene units with y pointing up. Paths are immutable: every operation returns
a new :class:`Path`, so a path sampled at time t can never be changed by a later call.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from animlib.geometry import bezier

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.intp]
BoolArray = NDArray[np.bool_]


def _frozen(array: NDArray[np.generic]) -> NDArray[np.generic]:
    array.flags.writeable = False
    return array


@dataclass(frozen=True, eq=False)
class Path:
    curves: FloatArray
    subpath_ids: IntArray
    closed: BoolArray

    def __post_init__(self) -> None:
        curves = np.array(self.curves, dtype=np.float64).reshape(-1, 4, 2)
        ids = np.array(self.subpath_ids, dtype=np.intp).reshape(-1)
        closed = np.array(self.closed, dtype=np.bool_).reshape(-1)
        if len(ids) != len(curves):
            raise ValueError(f"{len(curves)} curves but {len(ids)} subpath ids")
        if len(ids):
            steps = np.diff(ids)
            if ids[0] != 0 or np.any((steps != 0) & (steps != 1)):
                raise ValueError("subpath_ids must start at 0 and rise by 0 or 1")
            if ids[-1] + 1 != len(closed):
                raise ValueError(f"{ids[-1] + 1} subpaths but {len(closed)} closed flags")
        elif len(closed):
            raise ValueError("an empty path has no subpaths")
        object.__setattr__(self, "curves", _frozen(curves))
        object.__setattr__(self, "subpath_ids", _frozen(ids))
        object.__setattr__(self, "closed", _frozen(closed))

    # Construction

    @classmethod
    def empty(cls) -> Path:
        return cls(np.zeros((0, 4, 2)), np.zeros(0, dtype=np.intp), np.zeros(0, dtype=np.bool_))

    @classmethod
    def from_subpaths(cls, subpaths: Iterable[tuple[ArrayLike, bool]]) -> Path:
        """Build from ``(curves, closed)`` pairs, each ``curves`` being ``(m, 4, 2)``."""
        all_curves: list[FloatArray] = []
        ids: list[IntArray] = []
        closed: list[bool] = []
        for curves, is_closed in subpaths:
            arr = np.asarray(curves, dtype=np.float64).reshape(-1, 4, 2)
            if len(arr) == 0:
                continue
            ids.append(np.full(len(arr), len(closed), dtype=np.intp))
            all_curves.append(arr)
            closed.append(bool(is_closed))
        if not all_curves:
            return cls.empty()
        return cls(np.concatenate(all_curves), np.concatenate(ids), np.array(closed))

    @classmethod
    def polyline(cls, points: ArrayLike, closed: bool = False) -> Path:
        """Straight segments through ``points``; ``closed`` adds the segment back to the start."""
        pts = np.asarray(points, dtype=np.float64).reshape(-1, 2)
        if closed and not np.allclose(pts[0], pts[-1]):
            pts = np.vstack([pts, pts[:1]])
        curves = np.array([bezier.line(a, b) for a, b in itertools.pairwise(pts)])
        return cls.from_subpaths([(curves, closed)])

    @staticmethod
    def concat(paths: Sequence[Path]) -> Path:
        """All subpaths of ``paths`` as one path, in order."""
        return Path.from_subpaths(sp for p in paths for sp in p.subpaths())

    # Inspection

    @property
    def num_curves(self) -> int:
        return len(self.curves)

    @property
    def num_subpaths(self) -> int:
        return len(self.closed)

    def is_empty(self) -> bool:
        return self.num_curves == 0

    def subpaths(self) -> Iterator[tuple[FloatArray, bool]]:
        """Yield ``(curves, closed)`` for each subpath."""
        if self.is_empty():
            return
        bounds = np.flatnonzero(np.diff(self.subpath_ids)) + 1
        for i, chunk in enumerate(np.split(self.curves, bounds)):
            yield chunk, bool(self.closed[i])

    def bounds(self) -> tuple[FloatArray, FloatArray]:
        """``(min_xy, max_xy)`` of the control points, which contain the curves."""
        if self.is_empty():
            zero = np.zeros(2)
            return zero, zero.copy()
        pts = self.curves.reshape(-1, 2)
        return pts.min(axis=0), pts.max(axis=0)

    def center(self) -> FloatArray:
        lo, hi = self.bounds()
        result: FloatArray = (lo + hi) / 2
        return result

    @property
    def width(self) -> float:
        lo, hi = self.bounds()
        return float(hi[0] - lo[0])

    @property
    def height(self) -> float:
        lo, hi = self.bounds()
        return float(hi[1] - lo[1])

    def point_at(self, alpha: float) -> FloatArray:
        """Point a fraction ``alpha`` of the way along the curves, by curve count."""
        if self.is_empty():
            return np.zeros(2)
        alpha = float(np.clip(alpha, 0.0, 1.0))
        scaled = alpha * self.num_curves
        index = min(int(scaled), self.num_curves - 1)
        return bezier.evaluate(self.curves[index], scaled - index)

    # Transforms (all return new paths)

    def apply_matrix(self, matrix: ArrayLike) -> Path:
        """Apply a 2x2 linear or 3x3 affine (homogeneous) matrix to every control point."""
        m = np.asarray(matrix, dtype=np.float64)
        if m.shape == (2, 2):
            curves = self.curves @ m.T
        elif m.shape == (3, 3):
            curves = self.curves @ m[:2, :2].T + m[:2, 2]
        else:
            raise ValueError(f"expected a 2x2 or 3x3 matrix, got shape {m.shape}")
        return Path(curves, self.subpath_ids, self.closed)

    def shift(self, dx: float, dy: float = 0.0) -> Path:
        return Path(self.curves + np.array([dx, dy]), self.subpath_ids, self.closed)

    def move_to(self, x: float, y: float = 0.0) -> Path:
        cx, cy = self.center()
        return self.shift(x - cx, y - cy)

    def scale(self, factor: float | tuple[float, float], about: ArrayLike | None = None) -> Path:
        pivot = self.center() if about is None else np.asarray(about, dtype=np.float64)
        f = np.broadcast_to(np.asarray(factor, dtype=np.float64), (2,))
        return Path((self.curves - pivot) * f + pivot, self.subpath_ids, self.closed)

    def rotate(self, angle: float, about: ArrayLike | None = None) -> Path:
        pivot = self.center() if about is None else np.asarray(about, dtype=np.float64)
        c, s = np.cos(angle), np.sin(angle)
        rot = np.array([[c, -s], [s, c]])
        return Path((self.curves - pivot) @ rot.T + pivot, self.subpath_ids, self.closed)

    def reversed(self) -> Path:
        """Same shape, every subpath traced the other way."""
        return Path.from_subpaths(
            (curves[::-1, ::-1], closed) for curves, closed in self.subpaths()
        )

    def __repr__(self) -> str:
        return f"Path(curves={self.num_curves}, subpaths={self.num_subpaths})"
