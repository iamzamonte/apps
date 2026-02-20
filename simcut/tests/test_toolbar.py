import pytest
from PyQt6.QtWidgets import QApplication
from src.ui.toolbar import Toolbar
from src.utils.constants import DEFAULT_PEN_WIDTH


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


def test_toolbar_has_three_tools(app):
    toolbar = Toolbar()
    assert len(toolbar.tool_buttons) == 3


def test_toolbar_buttons_are_checkable(app):
    toolbar = Toolbar()
    for btn in toolbar.tool_buttons:
        assert btn.isCheckable()


def test_toolbar_has_open_button(app):
    toolbar = Toolbar()
    assert toolbar.open_btn is not None
    assert not toolbar.open_btn.isCheckable()


def test_toolbar_has_export_button(app):
    toolbar = Toolbar()
    assert toolbar.export_btn is not None
    assert not toolbar.export_btn.isCheckable()


def test_toolbar_has_batch_export_button(app):
    toolbar = Toolbar()
    assert toolbar.batch_export_btn is not None
    assert not toolbar.batch_export_btn.isCheckable()


def test_toolbar_open_signal_emitted(app, qtbot):
    toolbar = Toolbar()
    with qtbot.waitSignal(toolbar.open_requested, timeout=500):
        toolbar.open_btn.click()


def test_toolbar_export_signal_emitted(app, qtbot):
    toolbar = Toolbar()
    with qtbot.waitSignal(toolbar.export_requested, timeout=500):
        toolbar.export_btn.click()


def test_toolbar_batch_export_signal_emitted(app, qtbot):
    toolbar = Toolbar()
    with qtbot.waitSignal(toolbar.batch_export_requested, timeout=500):
        toolbar.batch_export_btn.click()


def test_toolbar_default_pen_width(app):
    toolbar = Toolbar()
    assert toolbar.pen_width == DEFAULT_PEN_WIDTH


def test_toolbar_pen_width_range(app):
    toolbar = Toolbar()
    toolbar.set_pen_width(15)
    assert toolbar.pen_width == 15


def test_toolbar_default_pen_color(app):
    from src.utils.constants import DEFAULT_PEN_COLOR
    toolbar = Toolbar()
    assert toolbar.pen_color == DEFAULT_PEN_COLOR


def test_toolbar_fill_color_default_none(app):
    toolbar = Toolbar()
    assert toolbar.fill_color is None


def test_sync_to_shape_updates_pen_width(app):
    """sync_to_shape 호출 시 pen_width가 반영된다."""
    toolbar = Toolbar()
    toolbar.sync_to_shape("#0000FF", 8, None)
    assert toolbar.pen_width == 8


def test_sync_to_shape_updates_pen_color(app):
    toolbar = Toolbar()
    toolbar.sync_to_shape("#00FF00", 3, None)
    assert toolbar.pen_color == "#00FF00"


def test_sync_to_shape_updates_fill_color(app):
    toolbar = Toolbar()
    toolbar.sync_to_shape("#FF0000", 2, "#FFFF00")
    assert toolbar.fill_color == "#FFFF00"


def test_sync_to_shape_no_signal_emitted(app):
    """sync_to_shape는 properties_changed 시그널을 발생시키지 않는다."""
    toolbar = Toolbar()
    emitted = []
    toolbar.properties_changed.connect(lambda *args: emitted.append(args))
    toolbar.sync_to_shape("#0000FF", 7, None)
    assert len(emitted) == 0


# ── 줌 컨트롤 테스트 ─────────────────────────────────────────

def test_toolbar_has_zoom_buttons(app):
    toolbar = Toolbar()
    assert toolbar._zoom_in_btn is not None
    assert toolbar._zoom_out_btn is not None


def test_toolbar_zoom_in_signal(app, qtbot):
    toolbar = Toolbar()
    with qtbot.waitSignal(toolbar.zoom_in_requested, timeout=500):
        toolbar._zoom_in_btn.click()


def test_toolbar_zoom_out_signal(app, qtbot):
    toolbar = Toolbar()
    with qtbot.waitSignal(toolbar.zoom_out_requested, timeout=500):
        toolbar._zoom_out_btn.click()


def test_toolbar_update_zoom_label(app):
    toolbar = Toolbar()
    toolbar.update_zoom_label(1.5)
    assert toolbar._zoom_label.text() == "150%"


def test_toolbar_zoom_label_default(app):
    toolbar = Toolbar()
    assert toolbar._zoom_label.text() == "100%"
