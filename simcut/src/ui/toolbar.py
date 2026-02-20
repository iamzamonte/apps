from __future__ import annotations
from typing import Optional, List
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QFrame
from PyQt6.QtCore import pyqtSignal
from src.core.shape_manager import ShapeType


class Toolbar(QWidget):
    tool_changed = pyqtSignal(object)    # ShapeType or None (선택 도구)
    open_requested = pyqtSignal()        # 불러오기 버튼 클릭
    export_requested = pyqtSignal()      # 내보내기 버튼 클릭

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        self.tool_buttons: List[QPushButton] = []

        # 파일 버튼 (불러오기 / 내보내기)
        self.open_btn = QPushButton("📂 불러오기")
        self.open_btn.clicked.connect(self.open_requested.emit)
        layout.addWidget(self.open_btn)

        self.export_btn = QPushButton("💾 내보내기")
        self.export_btn.clicked.connect(self.export_requested.emit)
        layout.addWidget(self.export_btn)

        # 구분선
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # 도형 도구 버튼
        self._add_tool("→ 선택", None)
        self._add_tool("□ 사각형", ShapeType.RECTANGLE)
        self._add_tool("○ 원", ShapeType.ELLIPSE)

    def _add_tool(self, label: str, shape_type: Optional[ShapeType]) -> None:
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.clicked.connect(lambda _, t=shape_type: self.tool_changed.emit(t))
        self.tool_buttons.append(btn)
        self.layout().addWidget(btn)
