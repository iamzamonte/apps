from __future__ import annotations
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem
)
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QEvent
from src.utils.theme import FILE_EXPLORER_STYLE, FILE_EXPLORER_TITLE_STYLE


class FileExplorer(QWidget):
    """우측 사이드 패널 - 불러온 파일 목록을 썸네일로 표시합니다."""

    file_selected = pyqtSignal(int)  # 파일 인덱스
    file_delete_requested = pyqtSignal(int)  # 삭제 요청 인덱스

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(140)
        self.setMaximumWidth(200)
        self.setStyleSheet(FILE_EXPLORER_STYLE)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 8, 6, 6)
        layout.setSpacing(6)

        title = QLabel("파일 목록")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(FILE_EXPLORER_TITLE_STYLE)
        layout.addWidget(title)

        self._list = QListWidget()
        self._list.setIconSize(QSize(120, 80))
        self._list.setSpacing(4)
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.installEventFilter(self)
        layout.addWidget(self._list)

    def add_file(self, path: str, thumbnail: QPixmap) -> None:
        """파일을 목록에 추가합니다."""
        filename = path.split("/")[-1]
        item = QListWidgetItem(QIcon(thumbnail), filename)
        item.setToolTip(path)
        self._list.addItem(item)
        self._list.setCurrentRow(self._list.count() - 1)

    def set_current(self, index: int) -> None:
        """현재 선택된 파일 항목을 하이라이트합니다."""
        self._list.setCurrentRow(index)

    def count(self) -> int:
        return self._list.count()

    def clear(self) -> None:
        """모든 파일 항목을 제거합니다."""
        self._list.clear()

    def remove_file(self, index: int) -> None:
        """인덱스에 해당하는 파일을 목록에서 제거합니다."""
        if 0 <= index < self._list.count():
            self._list.takeItem(index)

    def update_thumbnail(self, index: int, thumbnail: QPixmap) -> None:
        """지정 인덱스의 썸네일을 갱신합니다."""
        if 0 <= index < self._list.count():
            self._list.item(index).setIcon(QIcon(thumbnail))

    def eventFilter(self, source, event) -> bool:
        if source is self._list and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                current_row = self._list.currentRow()
                if current_row >= 0:
                    self.file_delete_requested.emit(current_row)
                return True
        return super().eventFilter(source, event)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        self.file_selected.emit(self._list.row(item))
