from __future__ import annotations
from PIL import Image
from pathlib import Path
from typing import Optional

_VALID_FORMATS = {"PNG", "JPEG", "WEBP", "BMP"}


class ImageHandler:
    def load(self, path: str) -> Image.Image:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Image not found: {path}")
        return Image.open(file_path).copy()

    def save(self, image: Image.Image, path: str, format: Optional[str] = None) -> None:
        file_path = Path(path)
        fmt = format or file_path.suffix.lstrip(".").upper()
        if fmt == "JPG":
            fmt = "JPEG"
        if fmt not in _VALID_FORMATS:
            raise ValueError(f"Unsupported format '{fmt}'. Supported: {sorted(_VALID_FORMATS)}")
        rgb_image = image.convert("RGB") if fmt == "JPEG" else image
        rgb_image.save(str(file_path), format=fmt)

    def get_info(self, image: Image.Image) -> dict:
        return {
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
        }
