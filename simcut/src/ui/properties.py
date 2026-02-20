from __future__ import annotations
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QSpinBox, QPushButton, QColorDialog
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor
from src.utils.constants import DEFAULT_PEN_COLOR, DEFAULT_PEN_WIDTH


class PropertiesPanel(QWidget):
    properties_changed = pyqtSignal(str, int, object)  # pen_color, pen_width, fill_color

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        self._pen_color: str = DEFAULT_PEN_COLOR
        self._fill_color: Optional[str] = None

        self._pen_btn = QPushButton("선 색상")
        self._pen_btn.clicked.connect(self._pick_pen_color)
        self._update_btn_style(self._pen_btn, self._pen_color)

        self._fill_btn = QPushButton("채움 없음")
        self._fill_btn.clicked.connect(self._pick_fill_color)

        self._width_spin = QSpinBox()
        self._width_spin.setRange(1, 20)
        self._width_spin.setValue(DEFAULT_PEN_WIDTH)
        self._width_spin.valueChanged.connect(self._emit)

        layout.addWidget(self._pen_btn)
        layout.addWidget(self._fill_btn)
        layout.addWidget(QLabel("굵기"))
        layout.addWidget(self._width_spin)

    @property
    def pen_color(self) -> str:
        return self._pen_color

    @property
    def pen_width(self) -> int:
        return self._width_spin.value()

    @property
    def fill_color(self) -> Optional[str]:
        return self._fill_color

    def set_pen_width(self, value: int) -> None:
        self._width_spin.setValue(value)

    def sync_to_shape(self, pen_color: str, pen_width: int, fill_color: Optional[str]) -> None:
        """선택된 도형 속성을 패널에 반영합니다 (시그널 발생 없이)."""
        self._width_spin.blockSignals(True)
        self._pen_color = pen_color
        self._fill_color = fill_color
        self._update_btn_style(self._pen_btn, pen_color)
        self._width_spin.setValue(pen_width)
        if fill_color:
            self._fill_btn.setText("채움 색상")
            self._update_btn_style(self._fill_btn, fill_color)
        else:
            self._fill_btn.setText("채움 없음")
            self._fill_btn.setStyleSheet("")
        self._width_spin.blockSignals(False)

    def _pick_pen_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._pen_color), self)
        if color.isValid():
            self._pen_color = color.name()
            self._update_btn_style(self._pen_btn, self._pen_color)
            self._emit()

    def _pick_fill_color(self) -> None:
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            self._fill_color = color.name()
            self._fill_btn.setText("채움 색상")
            self._update_btn_style(self._fill_btn, self._fill_color)
            self._emit()

    def _update_btn_style(self, btn: QPushButton, color: str) -> None:
        btn.setStyleSheet(f"background-color: {color}; color: white;")

    def _emit(self) -> None:
        self.properties_changed.emit(self._pen_color, self.pen_width, self._fill_color)
