import pytest
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


def test_file_menu_has_open_action(app):
    window = MainWindow()
    actions = [a.text() for a in window.menuBar().actions()[0].menu().actions()]
    assert any("Open" in a for a in actions)


def test_file_menu_has_export_action(app):
    window = MainWindow()
    actions = [a.text() for a in window.menuBar().actions()[0].menu().actions()]
    assert any("Export" in a for a in actions)


def test_edit_menu_has_undo(app):
    window = MainWindow()
    actions = [a.text() for a in window.menuBar().actions()[1].menu().actions()]
    assert any("Undo" in a for a in actions)


def test_edit_menu_has_redo(app):
    window = MainWindow()
    actions = [a.text() for a in window.menuBar().actions()[1].menu().actions()]
    assert any("Redo" in a for a in actions)


def test_window_has_canvas(app):
    window = MainWindow()
    assert window.canvas is not None


def test_window_has_toolbar(app):
    window = MainWindow()
    assert window.toolbar is not None


def test_toolbar_has_properties_controls(app):
    """속성 컨트롤(선 색상, 채움, 굵기)이 툴바에 통합되어 있다."""
    window = MainWindow()
    assert window.toolbar.pen_color is not None
    assert window.toolbar.pen_width > 0


def test_window_has_file_explorer(app):
    window = MainWindow()
    assert window.file_explorer is not None


def test_window_initial_file_count(app):
    window = MainWindow()
    assert window.file_count == 0


def test_switch_to_file_loads_slot(app, tmp_path):
    """_switch_to_file 호출 시 캔버스가 해당 슬롯으로 교체된다."""
    from PIL import Image
    from src.ui.canvas import _pil_to_pixmap
    from src.ui.main_window import _FileSlot
    from src.core.shape_manager import ShapeManager

    window = MainWindow()

    img = Image.new("RGB", (200, 100), (0, 0, 255))
    pixmap = _pil_to_pixmap(img)
    sm = ShapeManager()
    slot = _FileSlot(path="/fake/blue.png", image=img, scale=1.0, pixmap=pixmap, shape_manager=sm)

    window._file_slots.append(slot)
    window._switch_to_file(0)

    assert window.canvas.image is img
    assert window.file_count == 1


def test_multiple_slots_independent_shapes(app, tmp_path):
    """파일 슬롯별로 독립적인 ShapeManager를 가진다."""
    from PIL import Image
    from src.ui.canvas import _pil_to_pixmap
    from src.ui.main_window import _FileSlot
    from src.core.shape_manager import ShapeManager, Shape, ShapeType

    window = MainWindow()

    def make_slot(color, path):
        img = Image.new("RGB", (100, 100), color)
        pixmap = _pil_to_pixmap(img)
        sm = ShapeManager()
        return _FileSlot(path=path, image=img, scale=1.0, pixmap=pixmap, shape_manager=sm)

    slot0 = make_slot((255, 0, 0), "/fake/red.png")
    slot1 = make_slot((0, 0, 255), "/fake/blue.png")
    slot0.shape_manager.add(Shape(ShapeType.RECTANGLE, 0, 0, 10, 10, "#000", 1, None))

    window._file_slots.extend([slot0, slot1])
    window._switch_to_file(0)
    assert len(window.canvas._shape_manager.shapes) == 1

    window._switch_to_file(1)
    assert len(window.canvas._shape_manager.shapes) == 0
