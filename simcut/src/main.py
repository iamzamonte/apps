import sys
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.utils.constants import APP_NAME
from src.utils.theme import APP_STYLESHEET


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(APP_STYLESHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
