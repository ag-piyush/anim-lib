# Architecture

This is the condensed design. The full research behind it (a walkthrough of manim's source,
the alternatives, and the reasoning for each decision) is in the
[Manim Deep Dive & Build Plan](https://claude.ai/code/artifact/4d4e2858-3df5-4600-ab4c-7b147da8dd65).

## The model we keep from manim

1. **One geometry type for everything.** Shapes, SVG, text and maths all become a `Path` of
   cubic Béziers, so anything can morph into anything.
2. **An animation is a function of α in [0, 1]**, reshaped by an easing function. Staggering
   (`lag_ratio`) and grouping fall out of that.
3. **Morph by alignment.** Give two paths the same number of subpaths and curves, then lerp.
   See `geometry/align.py`.
4. **Record calls on a copy to make an animation** (`.animate`), and keep related things related
   (manim's updaters; derived values here).
5. **The camera is just another thing you animate.**

## What we do differently

| Decision | Choice | Why |
| --- | --- | --- |
| Time model | `play()` records into a timeline; frames are sampled at any t | Seeking, previews, parallel rendering and unit tests all depend on it. Manim can only reach frame N by running frames 0 to N−1 |
| Curves | Cubic Béziers | SVG, fonts, Typst output and Skia are all cubic natively |
| Transforms | Per-node affine, baked into points only when morphing | Moves and rotations stay cheap and exact |
| Rasteriser | Skia (`skia-python`) behind a `Renderer` protocol | Wheels for every platform, mature stroking; wgpu can follow for live preview and 3D |
| Text and maths | Typst (`pip install typst`), LaTeX as an optional plugin later | No TeX install; one pipeline for text and maths; bundled fonts make renders reproducible |
| Video | PyAV | Its wheels bundle FFmpeg |
| Reactivity | Derived values evaluated in dependency order at sample time | Deterministic at any t, unlike `dt`-based updaters |
| Config | Explicit `Camera` / `RenderConfig` and `Theme` objects | Nothing runs at import; several renders per process |
| Scope | 2D first | Most of manim's renderer complexity is 3D |

## Pipeline

```text
scene code ──record──▶ Timeline (plain data) ◀── text and SVG backends
                           │
                           ▼  per frame, any order, in parallel
            sample(t) ─▶ Theme resolves tokens ─▶ Renderer (Skia) ─▶ Encoder (PyAV)
                │                                                         │
           unit tests                                                  preview
```

Phase 0 (this commit) implements the bottom row by hand: `examples/phase0_morph.py` computes
each frame from t directly. Phase 1 replaces that loop with `Scene` and `Timeline`.

## Design system

Yes, but as a small `Theme` API inside the library, not a separate design kit. Manim already
has one in disguise (a 5-step palette per hue, a gap scale of 0.1/0.25/0.5/1.0, stroke 4, 1 s
`smooth` animations) welded into import-time constants. Ours resolves at render time so one
scene can render in light or dark, or at 16:9, 9:16 or 1:1, without edits.

| Layer | Tokens |
| --- | --- |
| Colour | Roles, not hues: `bg`, `fg`, `muted`, `accent`, `accent_2`, `positive`, `negative`, `highlight` |
| Type | Families for text, maths, code; a size scale `title` … `label` in scene units |
| Space and stroke | Gap scale, edge safe area, stroke weights, corner radius |
| Motion | Durations, easings (`standard`, `enter`, `exit`, `emphasis`), stagger steps |
| Frame | Aspect presets and frame height |

Primitives accept raw values or tokens; components accept only tokens.

## Roadmap

| Phase | Builds | Gate (what must be true to move on) |
| --- | --- | --- |
| 0 · Spike the stack | Path, shapes, morph alignment, Skia renderer, PyAV writer, Typst glyphs | A circle morphs into a square in a 3 s mp4, installed with pip alone. **Done** |
| 1 · Core model | Node tree with affine transforms, Timeline record and `sample(t)`, `play`/`wait`, Create, Fade, Transform, `.animate`, groups and lag | Frames rendered in shuffled order match frames rendered in order, pixel for pixel |
| 2 · Theme and text | Theme tokens, light and dark themes, aspect presets; Typst text and maths with addressable parts | One unchanged scene renders in both themes and all three aspects |
| 3 · Authoring loop | Notebook preview, browser scrubber, CLI over `render()`, frame cache, parallel rendering, derived values | Seek to any second of a scene without rendering what comes before it |
| 4 · v1.0 | Components (title card, callout, highlight, axes and graphs, code block), docs, frozen API under semver | Three real videos made end to end |

After v1: a wgpu live window, 3D, audio and voice-over sync, a visual editor.
