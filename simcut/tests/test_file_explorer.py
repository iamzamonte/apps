import pytest
from PIL import Image
from PyQt6.QtWidgets import QApplication
from src.ui.file_explorer import FileExplorer
from src.ui.canvas import _pil_to_pixmap


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


def _thumb():
    img = Image.new("RGB", (120, 80), (128, 128, 128))
    return _pil_to_pixmap(img)


def test_file_explorer_initial_count(app):
    explorer = FileExplorer()
    assert explorer.count() == 0


def test_file_explorer_add_file_increases_count(app):
    explorer = FileExplorer()
    explorer.add_file("/a/b/test.png", _thumb())
    assert explorer.count() == 1


def test_file_explorer_add_multiple_files(app):
    explorer = FileExplorer()
    explorer.add_file("/a/one.png", _thumb())
    explorer.add_file("/a/two.png", _thumb())
    explorer.add_file("/a/three.png", _thumb())
    assert explorer.count() == 3


def test_file_explorer_file_selected_signal(app):
    explorer = FileExplorer()
    explorer.add_file("/a/test.png", _thumb())

    received = []
    explorer.file_selected.connect(received.append)
    explorer._on_item_clicked(explorer._list.item(0))
    assert received == [0]


def test_file_explorer_signal_correct_index(app):
    explorer = FileExplorer()
    explorer.add_file("/a/zero.png", _thumb())
    explorer.add_file("/a/one.png", _thumb())
    explorer.add_file("/a/two.png", _thumb())

    received = []
    explorer.file_selected.connect(received.append)
    explorer._on_item_clicked(explorer._list.item(2))
    assert received == [2]


def test_file_explorer_set_current(app):
    explorer = FileExplorer()
    explorer.add_file("/a/a.png", _thumb())
    explorer.add_file("/a/b.png", _thumb())
    explorer.set_current(0)
    assert explorer._list.currentRow() == 0
