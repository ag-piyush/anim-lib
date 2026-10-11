"""Video files through PyAV, whose wheels bundle FFmpeg: no ``ffmpeg`` binary needed."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path as FilePath
from types import TracebackType

import av
import numpy as np
from av.video.stream import VideoStream

from animlib.render.base import RGBAImage

# Preferred encoder per container, first available wins
_CODECS: dict[str, tuple[str, ...]] = {
    ".mp4": ("libx264", "h264", "mpeg4"),
    ".mov": ("libx264", "h264", "prores_ks"),
    ".webm": ("libvpx-vp9", "libsvtav1"),
    ".mkv": ("libx264", "h264", "libvpx-vp9"),
}


def _available(codec: str) -> bool:
    try:
        av.codec.Codec(codec, "w")
    except Exception:
        return False
    return True


def pick_codec(suffix: str) -> str:
    for codec in _CODECS.get(suffix.lower(), ()):
        if _available(codec):
            return codec
    raise ValueError(f"no available encoder for {suffix!r} files; tried {_CODECS.get(suffix)}")


class VideoWriter:
    """Encode RGBA frames to a video file. Use as a context manager::

    with VideoWriter("out.mp4", 1920, 1080, fps=30) as video:
        video.write(frame)
    """

    def __init__(
        self,
        path: str | FilePath,
        width: int,
        height: int,
        fps: int | Fraction = 30,
        *,
        codec: str | None = None,
        quality: int = 18,
        pixel_format: str = "yuv420p",
    ) -> None:
        if pixel_format == "yuv420p" and (width % 2 or height % 2):
            raise ValueError(f"yuv420p needs even dimensions, got {width}x{height}")
        self.path = FilePath(path)
        self.width = width
        self.height = height
        self.frames_written = 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._container = av.open(str(self.path), mode="w")
        codec = codec or pick_codec(self.path.suffix)
        stream = self._container.add_stream(codec, rate=fps)
        if not isinstance(stream, VideoStream):
            raise ValueError(f"{codec!r} is not a video encoder")
        self._stream = stream
        self._stream.width = width
        self._stream.height = height
        self._stream.pix_fmt = pixel_format
        if codec in ("libx264", "libvpx-vp9", "libsvtav1"):
            # Constant quality: 0 is lossless for x264, ~18 is visually lossless
            self._stream.options = {"crf": str(quality)}
        self._closed = False

    def write(self, frame: RGBAImage) -> None:
        if self._closed:
            raise RuntimeError("writer is closed")
        if frame.shape != (self.height, self.width, 4):
            raise ValueError(f"frame is {frame.shape}, expected {(self.height, self.width, 4)}")
        video_frame = av.VideoFrame.from_ndarray(np.ascontiguousarray(frame), format="rgba")
        for packet in self._stream.encode(video_frame):
            self._container.mux(packet)
        self.frames_written += 1

    def close(self) -> None:
        if self._closed:
            return
        for packet in self._stream.encode(None):
            self._container.mux(packet)
        self._container.close()
        self._closed = True

    def __enter__(self) -> VideoWriter:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
