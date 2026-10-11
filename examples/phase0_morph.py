"""Phase 0 gate: a circle morphs into a square in a 3 s mp4, with nothing but pip installs.

Also writes an equation in glyph by glyph, to exercise the Typst text path and staggered
timing. This is deliberately hand-rolled frame by frame: the Scene and Timeline API that will
replace the loop below arrives in phase 1.

    uv run python examples/phase0_morph.py                  # 1080p, 30 fps
    uv run python examples/phase0_morph.py --resolution 480p
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path as FilePath

from animlib import (
    Camera,
    Color,
    DrawItem,
    Morph,
    Path,
    SkiaRenderer,
    Style,
    VideoWriter,
    easing,
    math,
    morph,
    save_png,
    shapes,
    text,
)
from animlib.render import RESOLUTIONS

BLUE = Color.parse("#58C4DD")
TEAL = Color.parse("#5CD0B3")
WHITE = Color.parse("#FFFFFF")

HOLD, MORPH = 0.5, 2.0
DURATION = HOLD + MORPH + HOLD


def frame_items(
    t: float, shape_morph: Morph, equation: list[Path], caption: list[Path]
) -> list[DrawItem]:
    """Everything on screen at time ``t`` seconds, computed from t alone."""
    alpha = easing.smooth(min(max((t - HOLD) / MORPH, 0.0), 1.0))
    color = BLUE.lerp(TEAL, alpha)
    items = [
        DrawItem(
            shape_morph.at(alpha),
            Style(fill=color.with_alpha(0.35), stroke=color, stroke_width=6),
        )
    ]
    # The equation fades in glyph by glyph across the morph
    progress = min(max((t - HOLD) / MORPH, 0.0), 1.0)
    for i, glyph in enumerate(equation):
        a = easing.smooth(easing.lagged(progress, i, len(equation), lag_ratio=0.3))
        if a > 0:
            items.append(DrawItem(glyph, Style(fill=WHITE.with_alpha(a), stroke=None)))
    items.extend(
        DrawItem(glyph, Style(fill=WHITE.with_alpha(0.6), stroke=None)) for glyph in caption
    )
    return items


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--resolution", default="1080p", choices=list(RESOLUTIONS))
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--out", type=FilePath, default=FilePath("renders/phase0_morph.mp4"))
    args = parser.parse_args()

    camera = Camera.at(args.resolution)
    renderer = SkiaRenderer()

    shape_morph = morph(shapes.circle(1.5).shift(0, 0.3), shapes.square(2.6).shift(0, 0.3))
    equation = [g.shift(0, 2.75) for g in math("e^(i pi) + 1 = 0", size=0.8)]
    caption = [g.shift(0, -2.9) for g in text("anim-lib · phase 0", size=0.45)]

    n_frames = round(DURATION * args.fps)
    started = time.perf_counter()
    buffer = None
    with VideoWriter(args.out, camera.width_px, camera.height_px, fps=args.fps) as video:
        for i in range(n_frames):
            t = i / args.fps
            buffer = renderer.render(frame_items(t, shape_morph, equation, caption), camera, buffer)
            video.write(buffer)
            if i == n_frames // 2:
                save_png(buffer, args.out.with_name(args.out.stem + "_mid.png"))
    elapsed = time.perf_counter() - started
    print(
        f"wrote {video.frames_written} frames ({DURATION:.1f} s at {args.fps} fps, "
        f"{camera.width_px}x{camera.height_px}) to {args.out} in {elapsed:.1f} s"
    )


if __name__ == "__main__":
    main()
