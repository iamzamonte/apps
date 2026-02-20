import pytest
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


def test_window_title(app):
    window = MainWindow()
    assert window.windowTitle() == "simcut"


def test_window_has_menubar(app):
    window = MainWindow()
    assert window.menuBar() is not None


def test_window_has_statusbar(app):
    window = MainWindow()
    assert window.statusBar() is not None


def test_window_minimum_size(app):
    window = MainWindow()
    assert window.minimumWidth() >= 800
    assert window.minimumHeight() >= 600
