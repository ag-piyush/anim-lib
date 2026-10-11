"""Still images."""

from __future__ import annotations

from pathlib import Path as FilePath

import numpy as np
import skia

from animlib.render.base import RGBAImage


def save_png(frame: RGBAImage, path: str | FilePath) -> FilePath:
    """Write a premultiplied RGBA frame, as renderers return it, to a PNG file."""
    target = FilePath(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    image = skia.Image.fromarray(
        np.ascontiguousarray(frame),
        colorType=skia.kRGBA_8888_ColorType,
        alphaType=skia.kPremul_AlphaType,
    )
    data = image.encodeToData(skia.kPNG, 100)
    if data is None:
        raise OSError(f"could not encode a PNG for {target}")
    target.write_bytes(bytes(data))
    return target
