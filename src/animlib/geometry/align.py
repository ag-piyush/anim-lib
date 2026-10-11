"""Make two paths the same shape of data, so one can be blended into the other.

This is manim's Transform trick: once both paths have the same number of subpaths, and each
pair of subpaths the same number of curves, a morph is a single vectorised lerp of two
``(n, 4, 2)`` arrays.

Three steps, all deterministic:

1. Pair subpaths by index. A subpath with no partner is matched with a copy of its partner's
   shape collapsed to a point at its own centre, so it grows out of (or shrinks into) where it
   stands rather than flying in from elsewhere.
2. Even out curve counts by cutting the longest curves first, which keeps the anchors evenly
   spread along each subpath.
3. For pairs of closed subpaths, pick the starting curve and direction of the second that best
   lines up with the first, so a morph does not twist or turn inside out.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass

import numpy as np

from animlib.geometry import bezier
from animlib.geometry.path import FloatArray, Path


def insert_curves(curves: FloatArray, extra: int) -> FloatArray:
    """The same subpath traced by ``extra`` more curves, cutting the longest first."""
    curves = np.asarray(curves, dtype=np.float64)
    if extra <= 0:
        return curves.copy()
    m = len(curves)
    lengths = bezier.approx_lengths(curves)
    counts = np.ones(m, dtype=int)
    if lengths.sum() <= 1e-12:
        # Nothing to measure: share the extra pieces out evenly
        counts += np.bincount(np.arange(extra) % m, minlength=m)
    else:
        # Max-heap on the length each curve's pieces would have after one more cut
        heap = [(-length, i) for i, length in enumerate(lengths)]
        heapq.heapify(heap)
        for _ in range(extra):
            _, i = heapq.heappop(heap)
            counts[i] += 1
            heapq.heappush(heap, (-lengths[i] / counts[i], i))
    return np.concatenate([bezier.subdivide(c, k) for c, k in zip(curves, counts, strict=True)])


def _best_cyclic_match(reference: FloatArray, candidate: FloatArray) -> FloatArray:
    """Rotate (and if it helps, reverse) a closed loop of curves to line up with ``reference``.

    Anchors are compared after centring each loop on its own mean, so the match is about
    shape and orientation, not where the two loops sit.
    """
    m = len(reference)
    a = reference[:, 0] - reference[:, 0].mean(axis=0)
    options = [candidate, candidate[::-1, ::-1]]
    shifts = (np.arange(m)[:, np.newaxis] + np.arange(m)[np.newaxis, :]) % m
    best: tuple[float, FloatArray] | None = None
    for option in options:
        b = option[:, 0] - option[:, 0].mean(axis=0)
        # cost[k] = sum of squared distances with the candidate started at curve k
        cost = ((a[np.newaxis] - b[shifts]) ** 2).sum(axis=(1, 2))
        k = int(np.argmin(cost))
        if best is None or cost[k] < best[0] - 1e-12:
            best = (float(cost[k]), np.roll(option, -k, axis=0))
    assert best is not None
    return best[1]


def _collapsed_like(curves: FloatArray) -> FloatArray:
    """A subpath with the same curve count, every point at the centre of ``curves``."""
    center = curves.reshape(-1, 2).mean(axis=0)
    return np.broadcast_to(center, curves.shape).copy()


def align(a: Path, b: Path, *, min_closed_curves: int = 16) -> tuple[Path, Path]:
    """Return copies of ``a`` and ``b`` with identical layout, ready to be blended.

    Pairs of closed subpaths are cut into at least ``min_closed_curves`` curves before their
    starting points are matched. Matching can only shift by whole curves, so with too few
    (a circle and a square have 4 each) the best match still turns the shape by up to half a
    curve's span (45° for that pair) on the way.
    """
    subs_a = list(a.subpaths())
    subs_b = list(b.subpaths())
    if not subs_a and not subs_b:
        return a, b
    n = max(len(subs_a), len(subs_b))
    out_a: list[tuple[FloatArray, bool]] = []
    out_b: list[tuple[FloatArray, bool]] = []
    for i in range(n):
        if i >= len(subs_a):
            cb, closed_b = subs_b[i]
            ca, closed_a = _collapsed_like(cb), closed_b
        elif i >= len(subs_b):
            ca, closed_a = subs_a[i]
            cb, closed_b = _collapsed_like(ca), closed_a
        else:
            (ca, closed_a), (cb, closed_b) = subs_a[i], subs_b[i]
        target = max(len(ca), len(cb))
        if closed_a and closed_b:
            target = max(target, min_closed_curves)
        ca = insert_curves(ca, target - len(ca))
        cb = insert_curves(cb, target - len(cb))
        if closed_a and closed_b:
            cb = _best_cyclic_match(ca, cb)
        out_a.append((ca, closed_a))
        out_b.append((cb, closed_b))
    return Path.from_subpaths(out_a), Path.from_subpaths(out_b)


@dataclass(frozen=True)
class Morph:
    """A blend between two aligned paths; call :meth:`at` with α in [0, 1]."""

    start: Path
    end: Path

    @classmethod
    def between(cls, a: Path, b: Path, *, min_closed_curves: int = 16) -> Morph:
        start, end = align(a, b, min_closed_curves=min_closed_curves)
        return cls(start, end)

    def at(self, alpha: float) -> Path:
        if alpha <= 0.0:
            return self.start
        if alpha >= 1.0:
            return self.end
        curves = self.start.curves + alpha * (self.end.curves - self.start.curves)
        # A closing segment is drawn only while both ends close; an open end converging on a
        # closed one closes its own gap continuously as α reaches 1
        closed = self.start.closed & self.end.closed
        return Path(curves, self.start.subpath_ids, closed)


def morph(a: Path, b: Path, *, min_closed_curves: int = 16) -> Morph:
    """Shorthand for :meth:`Morph.between`."""
    return Morph.between(a, b, min_closed_curves=min_closed_curves)
