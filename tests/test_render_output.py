from pathlib import Path as FilePath

import av
import numpy as np
import pytest

from animlib import Camera, DrawItem, SkiaRenderer, Style, VideoWriter, save_png, shapes

SMALL = Camera(width_px=160, height_px=90, frame_height=8.0, background=Camera().background)


def pixel(frame: np.ndarray, camera: Camera, x: float, y: float) -> np.ndarray:
    px, py = camera.to_pixels(np.array([x, y]))
    return np.asarray(frame[int(py), int(px)])


class TestCamera:
    def test_maps_centre_and_corners(self) -> None:
        cam = Camera(width_px=1920, height_px=1080, frame_height=8.0)
        assert np.allclose(cam.to_pixels(np.array([0.0, 0.0])), [960, 540])
        top_left = np.array([-cam.frame_width / 2, cam.frame_height / 2])
        assert np.allclose(cam.to_pixels(top_left), [0, 0])

    def test_named_resolutions(self) -> None:
        assert Camera.at("720p").width_px == 1280
        with pytest.raises(ValueError):
            Camera.at("8k")

    def test_stroke_scales_with_resolution(self) -> None:
        assert Camera.at("4k").stroke_px(4.0) == pytest.approx(8.0)


class TestSkiaRenderer:
    def test_background_only(self) -> None:
        frame = SkiaRenderer().render([], SMALL)
        assert frame.shape == (90, 160, 4)
        assert tuple(frame[0, 0]) == SMALL.background.to_rgba8()

    def test_fill_lands_inside_and_not_outside(self) -> None:
        item = DrawItem(shapes.square(2.0), Style.of(fill="#FF0000", stroke=None))
        frame = SkiaRenderer().render([item], SMALL)
        assert tuple(pixel(frame, SMALL, 0, 0)) == (255, 0, 0, 255)
        assert tuple(pixel(frame, SMALL, 3, 3)) == SMALL.background.to_rgba8()

    def test_reuses_the_output_buffer(self) -> None:
        buffer = np.zeros((90, 160, 4), dtype=np.uint8)
        out = SkiaRenderer().render([], SMALL, buffer)
        assert out is buffer
        with pytest.raises(ValueError):
            SkiaRenderer().render([], SMALL, np.zeros((10, 10, 4), dtype=np.uint8))

    def test_same_input_gives_identical_pixels(self) -> None:
        items = [DrawItem(shapes.star(), Style.of(fill="#58C4DD", stroke="#FFFFFF"))]
        a = SkiaRenderer().render(items, SMALL)
        b = SkiaRenderer().render(items, SMALL)
        assert np.array_equal(a, b)


class TestOutput:
    def test_png(self, tmp_path: FilePath) -> None:
        frame = SkiaRenderer().render([DrawItem(shapes.circle())], SMALL)
        target = save_png(frame, tmp_path / "frame.png")
        assert target.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

    def test_video_has_every_frame(self, tmp_path: FilePath) -> None:
        renderer = SkiaRenderer()
        target = tmp_path / "clip.mp4"
        with VideoWriter(target, SMALL.width_px, SMALL.height_px, fps=10) as video:
            for i in range(12):
                square = shapes.square(1.0).shift(-3 + i * 0.5, 0)
                video.write(renderer.render([DrawItem(square)], SMALL))
        with av.open(str(target)) as container:
            frames = list(container.decode(video=0))
        assert len(frames) == 12
        assert (frames[0].width, frames[0].height) == (160, 90)

    def test_video_rejects_odd_sizes(self, tmp_path: FilePath) -> None:
        with pytest.raises(ValueError):
            VideoWriter(tmp_path / "x.mp4", 161, 90)
