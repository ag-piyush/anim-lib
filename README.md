# anim-lib

A Python library for programmatic, explanatory animations, in the spirit of
[manim](https://github.com/3b1b/manim): everything on screen is a vector path, anything can
morph into anything, and time is something you script.

> **Status: phase 0 of 4.** The rendering stack works end to end (paths, morphs, text and maths,
> Skia rasterising, video out). The scene and timeline API is next. See the
> [roadmap](docs/architecture.md#roadmap).

## What is different from manim

| | manim | anim-lib |
| --- | --- | --- |
| Install | LaTeX, dvisvgm, Pango, an ffmpeg binary, a GPU stack | `pip install` only: Skia, Typst and PyAV ship as wheels |
| Time | `play()` mutates live objects frame by frame | `play()` will record into a timeline you can sample at any t |
| Config and style | Globals read at import (it even parses `sys.argv`) | Explicit `Camera`, and a `Theme` from phase 2 |
| Curves | Quadratic Béziers | Cubic Béziers, the native form of SVG, fonts and Skia |

The full reasoning, with a walkthrough of manim's source, is in
[docs/architecture.md](docs/architecture.md).

## Quick start

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/ag-piyush/anim-lib && cd anim-lib
uv sync                                     # creates .venv with the library and dev tools
uv run python examples/phase0_morph.py      # writes renders/phase0_morph.mp4
```

The example renders 3 seconds of a circle morphing into a square while an equation writes
itself in, at 1080p30, in about 3 seconds on a laptop CPU.

```python
from animlib import Camera, DrawItem, SkiaRenderer, Style, VideoWriter, easing, math, morph, shapes

camera = Camera.at("1080p")
renderer = SkiaRenderer()
m = morph(shapes.circle(1.5), shapes.square(2.6))
equation = math("e^(i pi) + 1 = 0", size=0.8)

with VideoWriter("out.mp4", camera.width_px, camera.height_px, fps=30) as video:
    for i in range(60):
        alpha = easing.smooth(i / 59)
        items = [DrawItem(m.at(alpha), Style.of(fill="#58C4DD", stroke="#FFFFFF"))]
        items += [DrawItem(g.shift(0, 2.75), Style.of(fill="#FFFFFF", stroke=None)) for g in equation]
        video.write(renderer.render(items, camera))
```

## Package layout

```text
src/animlib/
  core/       colour, easing (scene graph and timeline arrive in phase 1)
  geometry/   Path (cubic Béziers), shapes, morph alignment, SVG import
  text/       Typst backend: markup and maths to one path per glyph
  render/     Camera, Style, DrawItem, the Renderer protocol, the Skia renderer
  output/     video (PyAV) and PNG
```

`core` and `geometry` never import from `render`, `text` or `output`, so the evaluation layer
stays pure numpy and testable without fonts, a GPU or ffmpeg.

## Development

```bash
uv run pytest            # tests
uv run ruff check .      # lint
uv run ruff format .     # format
uv run mypy              # type-check the package (strict)
```

CI runs all four on Linux, macOS and Windows for every push and pull request.
