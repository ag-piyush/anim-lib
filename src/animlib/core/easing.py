"""Easing (rate) functions: maps from linear progress t in [0, 1] to eased progress.

Every function takes and returns a float, and also works element-wise on numpy arrays.
They fix 0 to 0 and 1 to 1, except the deliberate round trips (``there_and_back``).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

import numpy as np
from numpy.typing import NDArray

T = TypeVar("T", float, NDArray[np.float64])
Easing = Callable[[float], float]


def linear(t: T) -> T:
    return t


def smooth(t: T) -> T:
    """Quintic smoothstep, 6t⁵ − 15t⁴ + 10t³: zero first and second derivative at both ends.
    The default in manim, and here."""
    return t * t * t * (t * (6 * t - 15) + 10)


def ease_in(t: T) -> T:
    """Starts slow, arrives at full speed: the first half of ``smooth``, stretched."""
    return 2 * smooth(t / 2)


def ease_out(t: T) -> T:
    """Leaves at full speed, settles gently: the second half of ``smooth``, stretched."""
    return 2 * smooth((t + 1) / 2) - 1


def there_and_back(t: T) -> T:
    """Out to 1 at the midpoint and back to 0, smoothly."""
    return smooth(1 - abs(2 * t - 1))


def overshoot(t: T, pull: float = 1.5) -> T:
    """Goes past 1 and comes back, like a spring with little damping."""
    s = t - 1
    return 1 + s * s * ((pull + 1) * s + pull)


def lagged(alpha: float, index: int, count: int, lag_ratio: float) -> float:
    """Linear progress of part ``index`` of ``count`` when starts are staggered.

    With ``lag_ratio`` 0 every part runs together; with 1 each starts when the previous ends.
    The whole run is stretched to F = (count − 1)·lag + 1 part-lengths, as in manim.
    """
    if count <= 1:
        return float(np.clip(alpha, 0.0, 1.0))
    full = (count - 1) * lag_ratio + 1
    return float(np.clip(alpha * full - index * lag_ratio, 0.0, 1.0))


EASINGS: dict[str, Easing] = {
    "linear": linear,
    "smooth": smooth,
    "ease_in": ease_in,
    "ease_out": ease_out,
    "there_and_back": there_and_back,
    "overshoot": overshoot,
}
