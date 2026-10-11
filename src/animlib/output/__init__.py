"""Writing frames out: video files and still images."""

from animlib.output.image import save_png
from animlib.output.video import VideoWriter, pick_codec

__all__ = ["VideoWriter", "pick_codec", "save_png"]
