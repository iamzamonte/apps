import pytest
from pathlib import Path
from src.core.image_handler import ImageHandler

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample.png"
OUTPUT_BASE = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def cleanup():
    outputs = ["output.jpg", "output.png", "output.webp", "output.bmp"]
    yield
    for name in outputs:
        p = OUTPUT_BASE / name
        if p.exists():
            p.unlink()


def test_load_image_returns_pil_image():
    handler = ImageHandler()
    img = handler.load(str(FIXTURE_PATH))
    assert img is not None
    assert img.size == (100, 100)


def test_load_nonexistent_raises_error():
    handler = ImageHandler()
    with pytest.raises(FileNotFoundError):
        handler.load("nonexistent.png")


def test_save_jpeg():
    handler = ImageHandler()
    img = handler.load(str(FIXTURE_PATH))
    out = OUTPUT_BASE / "output.jpg"
    handler.save(img, str(out), format="JPEG")
    assert out.exists()


def test_save_png():
    handler = ImageHandler()
    img = handler.load(str(FIXTURE_PATH))
    out = OUTPUT_BASE / "output.png"
    handler.save(img, str(out), format="PNG")
    assert out.exists()


def test_save_webp():
    handler = ImageHandler()
    img = handler.load(str(FIXTURE_PATH))
    out = OUTPUT_BASE / "output.webp"
    handler.save(img, str(out), format="WEBP")
    assert out.exists()


def test_save_bmp():
    handler = ImageHandler()
    img = handler.load(str(FIXTURE_PATH))
    out = OUTPUT_BASE / "output.bmp"
    handler.save(img, str(out), format="BMP")
    assert out.exists()


def test_save_jpg_alias_normalized():
    handler = ImageHandler()
    img = handler.load(str(FIXTURE_PATH))
    out = OUTPUT_BASE / "output.jpg"
    handler.save(img, str(out), format="JPG")   # JPG → JPEG 정규화
    assert out.exists()


def test_save_invalid_format_raises_error():
    handler = ImageHandler()
    img = handler.load(str(FIXTURE_PATH))
    with pytest.raises(ValueError, match="Unsupported format"):
        handler.save(img, str(OUTPUT_BASE / "output.xyz"), format="XYZ")


def test_get_image_info():
    handler = ImageHandler()
    img = handler.load(str(FIXTURE_PATH))
    info = handler.get_info(img)
    assert info["width"] == 100
    assert info["height"] == 100
    assert info["mode"] == "RGB"
