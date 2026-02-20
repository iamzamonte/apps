from src.utils.constants import (
    SUPPORTED_FORMATS, DEFAULT_PEN_WIDTH, DEFAULT_PEN_COLOR,
    DEFAULT_FILL_COLOR, APP_NAME
)


def test_supported_formats_contains_common_types():
    assert "PNG" in SUPPORTED_FORMATS
    assert "JPEG" in SUPPORTED_FORMATS
    assert "WEBP" in SUPPORTED_FORMATS
    assert "BMP" in SUPPORTED_FORMATS


def test_default_pen_width_is_positive():
    assert DEFAULT_PEN_WIDTH > 0
    assert DEFAULT_PEN_WIDTH <= 20


def test_app_name():
    assert APP_NAME == "simcut"
