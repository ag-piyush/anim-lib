"""Colours as immutable RGBA floats in [0, 1].

Named colours and palettes belong to themes (see the roadmap, phase 2), not to this module:
here a colour is only ever a value.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Union

ColorLike = Union["Color", str, Sequence[float]]


@dataclass(frozen=True)
class Color:
    r: float
    g: float
    b: float
    a: float = 1.0

    def __post_init__(self) -> None:
        for name in ("r", "g", "b", "a"):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name}={value} is outside [0, 1]")
            object.__setattr__(self, name, value)

    @classmethod
    def parse(cls, value: ColorLike) -> Color:
        """Accepts a Color, ``"#rgb"``, ``"#rrggbb"``, ``"#rrggbbaa"``, or 3 or 4 floats in
        [0, 1]."""
        if isinstance(value, Color):
            return value
        if isinstance(value, str):
            return cls._from_hex(value)
        channels = [float(c) for c in value]
        if len(channels) not in (3, 4):
            raise ValueError(f"expected 3 or 4 channels, got {len(channels)}")
        return cls(*channels)

    @classmethod
    def _from_hex(cls, text: str) -> Color:
        digits = text.strip().removeprefix("#")
        if len(digits) in (3, 4):
            digits = "".join(d * 2 for d in digits)
        if len(digits) not in (6, 8):
            raise ValueError(f"not a hex colour: {text!r}")
        try:
            values = [int(digits[i : i + 2], 16) / 255 for i in range(0, len(digits), 2)]
        except ValueError:
            raise ValueError(f"not a hex colour: {text!r}") from None
        return cls(*values)

    def with_alpha(self, alpha: float) -> Color:
        return Color(self.r, self.g, self.b, alpha)

    def lerp(self, other: Color, t: float) -> Color:
        """Straight blend in RGBA; fine for short fades, not perceptually uniform. Channels are
        clamped, so an easing that overshoots cannot push a colour out of range."""

        def mix(x: float, y: float) -> float:
            return min(1.0, max(0.0, x + (y - x) * t))

        return Color(
            mix(self.r, other.r), mix(self.g, other.g), mix(self.b, other.b), mix(self.a, other.a)
        )

    def to_rgba8(self) -> tuple[int, int, int, int]:
        return (
            round(self.r * 255),
            round(self.g * 255),
            round(self.b * 255),
            round(self.a * 255),
        )

    def to_hex(self) -> str:
        r, g, b, a = self.to_rgba8()
        return f"#{r:02X}{g:02X}{b:02X}" + (f"{a:02X}" if a != 255 else "")
