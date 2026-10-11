# anim-lib

Python library for programmatic animations, modelled on 3b1b/manim. Design and roadmap:
`docs/architecture.md`. Read it before adding modules.

## Commands

- `uv sync` to set up; `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`,
  `uv run mypy` (strict) must all pass before committing.
- `uv run python examples/phase0_morph.py` renders a sample to `renders/` (git-ignored). After
  changing anything visual, render and look at frames rather than trusting tests alone.

## Conventions

- Import name is `animlib`; distribution name is `anim-lib` (`anim` is taken on PyPI).
- Scene units, y up, origin at the centre; the default frame is 8 units tall.
- `Path` and other values are immutable: operations return new objects. Keep it that way;
  sampling the timeline at t must never depend on what was sampled before.
- `core` and `geometry` must not import from `render`, `text` or `output`.
- Runtime dependencies must ship wheels for Linux, macOS and Windows. No system tools. The one
  known exception: on Linux, `skia-python` needs the system `libGL` and `libEGL`
  (`apt-get install libgl1 libegl1` on bare servers and CI).
- No colours, sizes or durations hard-coded in components; they come from the Theme (phase 2).
