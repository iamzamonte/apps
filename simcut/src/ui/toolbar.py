from __future__ import annotations
from typing import Optional, List
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QFrame, QLabel, QSpinBox, QColorDialog,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor
from src.core.shape_manager import ShapeType
from src.utils.constants import DEFAULT_PEN_COLOR, DEFAULT_PEN_WIDTH
from src.utils.theme import (
    TOOLBAR_STYLE, TOOL_BTN_FILE_STYLE, TOOL_BTN_SHAPE_STYLE,
    FILL_NONE_STYLE, color_btn_stylesheet, BORDER,
)


class Toolbar(QWidget):
    tool_changed = pyqtSignal(object)    # ShapeType or None (선택 도구)
    open_requested = pyqtSignal()        # 불러오기 버튼 클릭
    export_requested = pyqtSignal()      # 내보내기 버튼 클릭
    batch_export_requested = pyqtSignal()  # 일괄 내보내기 버튼 클릭
    properties_changed = pyqtSignal(str, int, object)  # pen_color, pen_width, fill_color
    zoom_in_requested = pyqtSignal()
    zoom_out_requested = pyqtSignal()
    zoom_reset_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(TOOLBAR_STYLE)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        self.tool_buttons: List[QPushButton] = []

        # 파일 버튼 (불러오기 / 내보내기 / 일괄 내보내기)
        self.open_btn = self._make_file_btn("불러오기")
        self.open_btn.clicked.connect(self.open_requested.emit)
        layout.addWidget(self.open_btn)

        self.export_btn = self._make_file_btn("내보내기")
        self.export_btn.clicked.connect(self.export_requested.emit)
        layout.addWidget(self.export_btn)

        self.batch_export_btn = self._make_file_btn("일괄 내보내기")
        self.batch_export_btn.clicked.connect(self.batch_export_requested.emit)
        layout.addWidget(self.batch_export_btn)

        # 구분선
        layout.addWidget(self._make_separator())

        # 도형 도구 버튼
        self._add_tool("선택", None)
        self._add_tool("사각형", ShapeType.RECTANGLE)
        self._add_tool("원", ShapeType.ELLIPSE)

        # 구분선
        layout.addWidget(self._make_separator())

        # 도형 속성 (선 색상, 채움, 굵기) — 도형 버튼 바로 오른쪽
        self._pen_color: str = DEFAULT_PEN_COLOR
        self._fill_color: Optional[str] = None

        self._pen_btn = QPushButton("선 색상")
        self._pen_btn.clicked.connect(self._pick_pen_color)
        self._pen_btn.setStyleSheet(color_btn_stylesheet(self._pen_color))
        layout.addWidget(self._pen_btn)

        self._fill_btn = QPushButton("채움 없음")
        self._fill_btn.clicked.connect(self._pick_fill_color)
        self._fill_btn.setStyleSheet(FILL_NONE_STYLE)
        layout.addWidget(self._fill_btn)

        width_label = QLabel("굵기")
        width_label.setStyleSheet("background: transparent; font-size: 12px;")
        layout.addWidget(width_label)
        self._width_spin = QSpinBox()
        self._width_spin.setRange(1, 20)
        self._width_spin.setValue(DEFAULT_PEN_WIDTH)
        self._width_spin.valueChanged.connect(self._emit_properties)
        layout.addWidget(self._width_spin)

        layout.addStretch()

        # 줌 컨트롤 (오른쪽 끝)
        layout.addWidget(self._make_separator())
        self._zoom_out_btn = QPushButton("-")
        self._zoom_out_btn.setFixedWidth(28)
        self._zoom_out_btn.setStyleSheet(TOOL_BTN_FILE_STYLE)
        self._zoom_out_btn.clicked.connect(self.zoom_out_requested.emit)
        layout.addWidget(self._zoom_out_btn)

        self._zoom_label = QLabel("100%")
        self._zoom_label.setFixedWidth(48)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zoom_label.setStyleSheet("background: transparent; font-size: 12px;")
        self._zoom_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self._zoom_label.mousePressEvent = lambda _: self.zoom_reset_requested.emit()
        layout.addWidget(self._zoom_label)

        self._zoom_in_btn = QPushButton("+")
        self._zoom_in_btn.setFixedWidth(28)
        self._zoom_in_btn.setStyleSheet(TOOL_BTN_FILE_STYLE)
        self._zoom_in_btn.clicked.connect(self.zoom_in_requested.emit)
        layout.addWidget(self._zoom_in_btn)

    # ── 속성 접근자 ──────────────────────────────────────────────
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

    def update_zoom_label(self, zoom: float) -> None:
        """줌 레벨 라벨을 갱신합니다."""
        self._zoom_label.setText(f"{int(zoom * 100)}%")

    def sync_to_shape(self, pen_color: str, pen_width: int, fill_color: Optional[str]) -> None:
        """선택된 도형 속성을 패널에 반영합니다 (시그널 발생 없이)."""
        self._width_spin.blockSignals(True)
        self._pen_color = pen_color
        self._fill_color = fill_color
        self._pen_btn.setStyleSheet(color_btn_stylesheet(pen_color))
        self._width_spin.setValue(pen_width)
        if fill_color:
            self._fill_btn.setText("채움 색상")
            self._fill_btn.setStyleSheet(color_btn_stylesheet(fill_color))
        else:
            self._fill_btn.setText("채움 없음")
            self._fill_btn.setStyleSheet(FILL_NONE_STYLE)
        self._width_spin.blockSignals(False)

    # ── 내부 헬퍼 ────────────────────────────────────────────────
    def _make_file_btn(self, label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setStyleSheet(TOOL_BTN_FILE_STYLE)
        return btn

    def _make_separator(self) -> QFrame:
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        separator.setStyleSheet(f"color: {BORDER}; max-width: 1px;")
        return separator

    def _add_tool(self, label: str, shape_type: Optional[ShapeType]) -> None:
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.setStyleSheet(TOOL_BTN_SHAPE_STYLE)
        btn.clicked.connect(lambda _, t=shape_type: self.tool_changed.emit(t))
        self.tool_buttons.append(btn)
        self.layout().addWidget(btn)

    def _pick_pen_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._pen_color), self)
        if color.isValid():
            self._pen_color = color.name()
            self._pen_btn.setStyleSheet(color_btn_stylesheet(self._pen_color))
            self._emit_properties()

    def _pick_fill_color(self) -> None:
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            self._fill_color = color.name()
            self._fill_btn.setText("채움 색상")
            self._fill_btn.setStyleSheet(color_btn_stylesheet(self._fill_color))
            self._emit_properties()

    def _emit_properties(self) -> None:
        self.properties_changed.emit(self._pen_color, self.pen_width, self._fill_color)
