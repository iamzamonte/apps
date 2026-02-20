from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QLabel, QFileDialog, QMessageBox, QSplitter
)
from PyQt6.QtGui import QKeySequence, QAction, QPixmap
from PyQt6.QtCore import Qt
from PIL import Image
from src.ui.canvas import Canvas, _pil_to_pixmap
from src.ui.toolbar import Toolbar
from src.ui.properties import PropertiesPanel
from src.ui.file_explorer import FileExplorer
from src.core.shape_manager import ShapeManager
from src.core.image_handler import ImageHandler
from src.utils.constants import (
    APP_NAME, OPEN_FILE_FILTER, SAVE_FILE_FILTER
)

# 파일 탐색기 썸네일 크기
_THUMB_W = 120
_THUMB_H = 80


@dataclass
class _FileSlot:
    """파일 하나에 해당하는 이미지/스케일/픽스맵/도형 세트."""
    path: str
    image: Image.Image
    scale: float
    pixmap: QPixmap
    shape_manager: ShapeManager


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(900, 660)
        self._handler = ImageHandler()
        self._file_slots: List[_FileSlot] = []
        self._current_slot_index: int = -1
        # 기본 ShapeManager (파일 로드 전 캔버스용)
        self._default_sm = ShapeManager()
        self._setup_menubar()
        self._setup_central()
        self._setup_statusbar()

    # ── 공개 속성 ────────────────────────────────────────────────
    @property
    def canvas(self) -> Canvas:
        return self._canvas

    @property
    def toolbar(self) -> Toolbar:
        return self._toolbar

    @property
    def properties_panel(self) -> PropertiesPanel:
        return self._props

    @property
    def file_explorer(self) -> FileExplorer:
        return self._explorer

    @property
    def file_count(self) -> int:
        return len(self._file_slots)

    # ── 메뉴바 ──────────────────────────────────────────────────
    def _setup_menubar(self) -> None:
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("File")
        open_action = QAction("Open…", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self._open_file)
        export_action = QAction("Export…", self)
        export_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        export_action.triggered.connect(self._export_file)
        file_menu.addAction(open_action)
        file_menu.addAction(export_action)

        # Edit
        edit_menu = mb.addMenu("Edit")
        undo_action = QAction("Undo", self)
        undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        undo_action.triggered.connect(self._undo)
        redo_action = QAction("Redo", self)
        redo_action.setShortcut(QKeySequence("Ctrl+Shift+Z"))
        redo_action.triggered.connect(self._redo)
        edit_menu.addAction(undo_action)
        edit_menu.addAction(redo_action)

        # View
        mb.addMenu("View")

    # ── 중앙 위젯 ───────────────────────────────────────────────
    def _setup_central(self) -> None:
        self._canvas = Canvas(self._default_sm)
        self._toolbar = Toolbar()
        self._props = PropertiesPanel()
        self._explorer = FileExplorer()

        # 도구바 + 속성 패널 행
        tool_row = QWidget()
        tool_row.setMaximumHeight(44)
        h_layout = QHBoxLayout(tool_row)
        h_layout.setContentsMargins(4, 2, 4, 2)
        h_layout.addWidget(self._toolbar)
        h_layout.addStretch()
        h_layout.addWidget(self._props)

        # 캔버스 스크롤 영역
        self._scroll = QScrollArea()
        self._scroll.setWidget(self._canvas)
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scroll.setWidgetResizable(False)

        # 캔버스 영역(스크롤) + 파일 탐색기를 수평 분할
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._scroll)
        splitter.addWidget(self._explorer)
        splitter.setStretchFactor(0, 1)   # 캔버스 영역이 늘어남
        splitter.setStretchFactor(1, 0)   # 탐색기는 고정 폭 유지
        splitter.setSizes([700, 160])

        # 전체 레이아웃
        container = QWidget()
        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(0)
        v_layout.addWidget(tool_row)
        v_layout.addWidget(splitter, stretch=1)
        self.setCentralWidget(container)

        # 시그널 연결
        self._toolbar.open_requested.connect(self._open_file)
        self._toolbar.export_requested.connect(self._export_file)
        self._toolbar.tool_changed.connect(self._on_tool_changed)
        self._props.properties_changed.connect(self._on_props_changed)
        self._explorer.file_selected.connect(self._switch_to_file)
        self._canvas.selection_changed.connect(self._on_selection_changed)

    # ── 상태바 ──────────────────────────────────────────────────
    def _setup_statusbar(self) -> None:
        self._status_label = QLabel("Ready")
        self.statusBar().addWidget(self._status_label)

    # ── 파일 슬롯 관리 ──────────────────────────────────────────
    def _build_slot(self, path: str, max_size: Optional[tuple]) -> _FileSlot:
        """경로에서 파일 슬롯을 생성합니다."""
        image = self._handler.load(path)
        scale = self._canvas._calc_scale(image.size, max_size)
        display_w = int(image.width * scale)
        display_h = int(image.height * scale)
        display_img = (
            image.resize((display_w, display_h), Image.LANCZOS)
            if scale != 1.0 else image
        )
        pixmap = _pil_to_pixmap(display_img)
        return _FileSlot(
            path=path,
            image=image,
            scale=scale,
            pixmap=pixmap,
            shape_manager=ShapeManager(),
        )

    def _make_thumbnail(self, image: Image.Image) -> QPixmap:
        """파일 탐색기용 썸네일 QPixmap을 생성합니다."""
        thumb = image.copy()
        thumb.thumbnail((_THUMB_W, _THUMB_H), Image.LANCZOS)
        return _pil_to_pixmap(thumb)

    def _switch_to_file(self, index: int) -> None:
        """파일 탐색기에서 파일 선택 시 캔버스를 전환합니다."""
        if not (0 <= index < len(self._file_slots)):
            return
        self._current_slot_index = index
        slot = self._file_slots[index]
        self._canvas.set_slot(slot.image, slot.scale, slot.pixmap, slot.shape_manager)
        self._explorer.set_current(index)
        self._status_label.setText(slot.path.split("/")[-1])

    # ── 액션 핸들러 ─────────────────────────────────────────────
    def _open_file(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Image", "", OPEN_FILE_FILTER
        )
        if not paths:
            return
        vp = self._scroll.viewport().size()
        max_size = (max(vp.width() - 10, 400), max(vp.height() - 10, 300))
        for path in paths:
            try:
                slot = self._build_slot(path, max_size)
                thumb = self._make_thumbnail(slot.image)
                self._file_slots.append(slot)
                self._explorer.add_file(path, thumb)
            except Exception as e:
                QMessageBox.warning(self, "열기 실패", f"이미지를 열 수 없습니다.\n{path}\n{e}")
        if self._file_slots:
            self._switch_to_file(len(self._file_slots) - 1)

    def _export_file(self) -> None:
        if self._canvas.image is None:
            QMessageBox.information(self, "내보내기", "먼저 이미지를 불러오세요.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Image", "", SAVE_FILE_FILTER
        )
        if not path:
            return
        try:
            composite = self._canvas.render_to_image()
            self._handler.save(composite, path)
            self._status_label.setText(f"Exported: {path.split('/')[-1]}")
        except Exception as e:
            QMessageBox.warning(self, "내보내기 실패", f"이미지를 저장할 수 없습니다.\n{e}")
            self._status_label.setText("Ready")

    def _undo(self) -> None:
        if 0 <= self._current_slot_index < len(self._file_slots):
            self._file_slots[self._current_slot_index].shape_manager.undo()
        self._canvas.update()

    def _redo(self) -> None:
        if 0 <= self._current_slot_index < len(self._file_slots):
            self._file_slots[self._current_slot_index].shape_manager.redo()
        self._canvas.update()

    def _on_tool_changed(self, shape_type) -> None:
        if shape_type is None:
            self._canvas.select_mode = True
        else:
            self._canvas.select_mode = False
            self._canvas.current_shape_type = shape_type

    def _on_selection_changed(self, shape) -> None:
        """도형 선택/해제 시 속성 패널을 해당 도형의 값으로 동기화합니다."""
        if shape is not None:
            self._props.sync_to_shape(shape.pen_color, shape.pen_width, shape.fill_color)

    def _on_props_changed(self, pen_color: str, pen_width: int, fill_color: Optional[str]) -> None:
        self._canvas.pen_color = pen_color
        self._canvas.pen_width = pen_width
        self._canvas.fill_color = fill_color
        # 선택된 도형이 있으면 실시간으로 스타일 반영
        self._canvas.apply_style_to_selected(pen_color, pen_width, fill_color)
