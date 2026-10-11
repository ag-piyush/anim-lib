"""CPU rasteriser on Skia (``skia-python``): mature anti-aliasing, stroking and joins, and
binary wheels for Linux, macOS and Windows."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import skia

from animlib.core.color import Color
from animlib.geometry.path import Path
from animlib.render.base import Camera, DrawItem, RGBAImage, Style

_JOINS = {
    "miter": skia.Paint.kMiter_Join,
    "round": skia.Paint.kRound_Join,
    "bevel": skia.Paint.kBevel_Join,
}
_CAPS = {
    "butt": skia.Paint.kButt_Cap,
    "round": skia.Paint.kRound_Cap,
    "square": skia.Paint.kSquare_Cap,
}


def _skia_color(color: Color) -> int:
    r, g, b, a = color.to_rgba8()
    return int(skia.Color(r, g, b, a))


def to_skia_path(path: Path, camera: Camera) -> skia.Path:
    """Build a Skia path in pixel coordinates."""
    out = skia.Path()
    for curves, closed in path.subpaths():
        px = camera.to_pixels(curves)
        out.moveTo(*px[0, 0])
        for _, c1, c2, p3 in px:
            out.cubicTo(c1[0], c1[1], c2[0], c2[1], p3[0], p3[1])
        if closed:
            out.close()
    return out


class SkiaRenderer:
    def render(
        self,
        items: Sequence[DrawItem],
        camera: Camera,
        out: RGBAImage | None = None,
    ) -> RGBAImage:
        shape = (camera.height_px, camera.width_px, 4)
        if out is None:
            out = np.empty(shape, dtype=np.uint8)
        elif out.shape != shape or out.dtype != np.uint8 or not out.flags.c_contiguous:
            raise ValueError(f"out must be a C-contiguous uint8 array of shape {shape}")
        surface = skia.Surface(
            out, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType
        )
        canvas = surface.getCanvas()
        canvas.clear(_skia_color(camera.background))
        for item in items:
            if item.path.is_empty():
                continue
            self._draw(canvas, to_skia_path(item.path, camera), item.style, camera)
        surface.flushAndSubmit()
        return out

    @staticmethod
    def _draw(canvas: skia.Canvas, path: skia.Path, style: Style, camera: Camera) -> None:
        if style.fill is not None and style.fill.a > 0:
            canvas.drawPath(
                path,
                skia.Paint(
                    AntiAlias=True, Style=skia.Paint.kFill_Style, Color=_skia_color(style.fill)
                ),
            )
        if style.stroke is not None and style.stroke.a > 0 and style.stroke_width > 0:
            canvas.drawPath(
                path,
                skia.Paint(
                    AntiAlias=True,
                    Style=skia.Paint.kStroke_Style,
                    Color=_skia_color(style.stroke),
                    StrokeWidth=camera.stroke_px(style.stroke_width),
                    StrokeJoin=_JOINS[style.line_join],
                    StrokeCap=_CAPS[style.line_cap],
                ),
            )
