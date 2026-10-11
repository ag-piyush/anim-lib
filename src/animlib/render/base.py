"""What a renderer is given, and what it must return.

A frame is a flat, ordered list of :class:`DrawItem` (a path plus its style), drawn back to
front, seen through a :class:`Camera`. Renderers are interchangeable behind
:class:`Renderer`; the Skia one is the default.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from typing import Literal, Protocol

import numpy as np
from numpy.typing import NDArray

from animlib.core.color import Color, ColorLike
from animlib.geometry.path import FloatArray, Path

RGBAImage = NDArray[np.uint8]
"""``(height, width, 4)`` uint8, RGBA, premultiplied alpha, top row first."""

# Stroke widths are given in pixels as they would be on a frame this many pixels tall, then
# scaled, so a drawing looks the same at every resolution.
REFERENCE_HEIGHT_PX = 1080

RESOLUTIONS: dict[str, tuple[int, int]] = {
    "480p": (854, 480),
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "1440p": (2560, 1440),
    "4k": (3840, 2160),
}


def _color(value: ColorLike | None) -> Color | None:
    return None if value is None else Color.parse(value)


@dataclass(frozen=True)
class Style:
    fill: Color | None = None
    stroke: Color | None = field(default_factory=lambda: Color(1.0, 1.0, 1.0))
    stroke_width: float = 4.0
    """Pixels on a 1080-pixel-tall frame; scaled with the output resolution."""
    line_join: Literal["miter", "round", "bevel"] = "round"
    line_cap: Literal["butt", "round", "square"] = "round"

    @classmethod
    def of(
        cls,
        fill: ColorLike | None = None,
        stroke: ColorLike | None = "#FFFFFF",
        stroke_width: float = 4.0,
    ) -> Style:
        """Convenience constructor taking any colour-like values."""
        return cls(fill=_color(fill), stroke=_color(stroke), stroke_width=stroke_width)


@dataclass(frozen=True)
class DrawItem:
    path: Path
    style: Style = field(default_factory=Style)


@dataclass(frozen=True)
class Camera:
    """Maps scene units (y up, origin at the centre) to output pixels (y down)."""

    width_px: int = 1920
    height_px: int = 1080
    frame_height: float = 8.0
    """How many scene units are visible top to bottom."""
    center: tuple[float, float] = (0.0, 0.0)
    background: Color = field(default_factory=lambda: Color.parse("#333333"))

    @classmethod
    def at(
        cls,
        resolution: str,
        *,
        frame_height: float = 8.0,
        background: ColorLike = "#333333",
    ) -> Camera:
        """A camera at a named resolution such as ``"720p"``, see :data:`RESOLUTIONS`."""
        if resolution not in RESOLUTIONS:
            raise ValueError(f"unknown resolution {resolution!r}; choose from {list(RESOLUTIONS)}")
        width, height = RESOLUTIONS[resolution]
        return cls(
            width_px=width,
            height_px=height,
            frame_height=frame_height,
            background=Color.parse(background),
        )

    @property
    def frame_width(self) -> float:
        return self.frame_height * self.width_px / self.height_px

    @property
    def pixels_per_unit(self) -> float:
        return self.height_px / self.frame_height

    def with_resolution(self, width_px: int, height_px: int) -> Camera:
        return replace(self, width_px=width_px, height_px=height_px)

    def to_pixels(self, points: FloatArray) -> FloatArray:
        """Scene points ``(..., 2)`` to pixel coordinates."""
        ppu = self.pixels_per_unit
        out = np.empty_like(points, dtype=np.float64)
        out[..., 0] = (points[..., 0] - self.center[0]) * ppu + self.width_px / 2
        out[..., 1] = self.height_px / 2 - (points[..., 1] - self.center[1]) * ppu
        return out

    def stroke_px(self, width: float) -> float:
        return width * self.height_px / REFERENCE_HEIGHT_PX


class Renderer(Protocol):
    def render(
        self,
        items: Sequence[DrawItem],
        camera: Camera,
        out: RGBAImage | None = None,
    ) -> RGBAImage:
        """Draw ``items`` back to front over the camera's background.

        ``out``, if given, must be a C-contiguous ``(height, width, 4)`` uint8 array; it is
        drawn into and returned, which saves an allocation per frame.
        """
        ...
