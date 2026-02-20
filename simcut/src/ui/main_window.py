from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QLabel, QFileDialog, QMessageBox, QSplitter,
    QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QProgressDialog, QCheckBox, QPushButton,
)
from PyQt6.QtGui import QKeySequence, QAction, QPixmap
from PyQt6.QtCore import Qt
from PIL import Image
from src.ui.canvas import Canvas, _pil_to_pixmap
from src.ui.toolbar import Toolbar
from src.ui.file_explorer import FileExplorer
from src.core.shape_manager import ShapeManager
from src.core.image_handler import ImageHandler
from src.utils.constants import (
    APP_NAME, OPEN_FILE_FILTER, SAVE_FILE_FILTER, SUPPORTED_FORMATS,
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
    zoom: float = 1.0


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
        batch_export_action = QAction("Batch Export…", self)
        batch_export_action.setShortcut(QKeySequence("Ctrl+Shift+E"))
        batch_export_action.triggered.connect(self._batch_export)
        file_menu.addAction(open_action)
        file_menu.addAction(export_action)
        file_menu.addAction(batch_export_action)

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
        view_menu = mb.addMenu("View")
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setShortcut(QKeySequence("Ctrl+="))
        zoom_in_action.triggered.connect(lambda: self._canvas.zoom_in())
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setShortcut(QKeySequence("Ctrl+-"))
        zoom_out_action.triggered.connect(lambda: self._canvas.zoom_out())
        zoom_reset_action = QAction("Reset Zoom", self)
        zoom_reset_action.setShortcut(QKeySequence("Ctrl+0"))
        zoom_reset_action.triggered.connect(lambda: self._canvas.zoom_reset())
        view_menu.addAction(zoom_in_action)
        view_menu.addAction(zoom_out_action)
        view_menu.addAction(zoom_reset_action)

    # ── 중앙 위젯 ───────────────────────────────────────────────
    def _setup_central(self) -> None:
        self._canvas = Canvas(self._default_sm)
        self._toolbar = Toolbar()
        self._explorer = FileExplorer()

        # 도구바 행 (도형 도구 + 속성이 통합됨)
        tool_row = QWidget()
        tool_row.setMaximumHeight(48)
        h_layout = QHBoxLayout(tool_row)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)
        h_layout.addWidget(self._toolbar)

        # 캔버스 스크롤 영역
        self._scroll = QScrollArea()
        self._scroll.setWidget(self._canvas)
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scroll.setWidgetResizable(False)

        # 왼쪽: 도구바 + 캔버스 (세로 스택)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        left_layout.addWidget(tool_row)
        left_layout.addWidget(self._scroll, stretch=1)

        # 캔버스 영역 + 파일 탐색기를 수평 분할
        # 파일 탐색기가 전체 높이를 차지하도록 레이아웃 일치
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self._explorer)
        splitter.setStretchFactor(0, 1)   # 캔버스 영역이 늘어남
        splitter.setStretchFactor(1, 0)   # 탐색기는 고정 폭 유지
        splitter.setSizes([700, 160])

        # 전체 레이아웃
        container = QWidget()
        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(0)
        v_layout.addWidget(splitter, stretch=1)
        self.setCentralWidget(container)

        # 시그널 연결
        self._toolbar.open_requested.connect(self._open_file)
        self._toolbar.export_requested.connect(self._export_file)
        self._toolbar.batch_export_requested.connect(self._batch_export)
        self._toolbar.tool_changed.connect(self._on_tool_changed)
        self._toolbar.properties_changed.connect(self._on_props_changed)
        self._toolbar.zoom_in_requested.connect(self._canvas.zoom_in)
        self._toolbar.zoom_out_requested.connect(self._canvas.zoom_out)
        self._toolbar.zoom_reset_requested.connect(self._canvas.zoom_reset)
        self._canvas.zoom_changed.connect(self._on_zoom_changed)
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
        # 현재 슬롯의 줌 레벨 저장
        if 0 <= self._current_slot_index < len(self._file_slots):
            self._file_slots[self._current_slot_index].zoom = self._canvas.zoom
        self._current_slot_index = index
        slot = self._file_slots[index]
        self._canvas.set_slot(slot.image, slot.scale, slot.pixmap, slot.shape_manager, slot.zoom)
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

    def _batch_export(self) -> None:
        """선택한 파일에 도형 합성 결과를 일괄 내보내기합니다."""
        if not self._file_slots:
            QMessageBox.information(self, "일괄 내보내기", "먼저 이미지를 불러오세요.")
            return

        # 파일 선택 + 포맷 설정 다이얼로그
        dialog = QDialog(self)
        dialog.setWindowTitle("일괄 내보내기 설정")
        dialog.setMinimumWidth(380)
        layout = QVBoxLayout(dialog)

        # 파일 선택 영역
        file_label = QLabel("내보낼 파일 선택:")
        layout.addWidget(file_label)

        filenames: List[str] = [Path(slot.path).name for slot in self._file_slots]
        checkboxes: List[QCheckBox] = []
        for name in filenames:
            cb = QCheckBox(name)
            cb.setChecked(True)
            checkboxes.append(cb)
            layout.addWidget(cb)

        def _update_order_labels() -> None:
            order = 1
            for i, cb in enumerate(checkboxes):
                if cb.isChecked():
                    cb.setText(f"{order}. {filenames[i]}")
                    order += 1
                else:
                    cb.setText(filenames[i])

        _update_order_labels()
        for cb in checkboxes:
            cb.toggled.connect(lambda _: _update_order_labels())

        # 전체 선택/해제 버튼
        toggle_row = QHBoxLayout()
        select_all_btn = QPushButton("전체 선택")
        deselect_all_btn = QPushButton("전체 해제")
        select_all_btn.clicked.connect(lambda: [cb.setChecked(True) for cb in checkboxes])
        deselect_all_btn.clicked.connect(lambda: [cb.setChecked(False) for cb in checkboxes])
        toggle_row.addWidget(select_all_btn)
        toggle_row.addWidget(deselect_all_btn)
        toggle_row.addStretch()
        layout.addLayout(toggle_row)

        # 포맷 선택
        form = QFormLayout()
        format_combo = QComboBox()
        for fmt in SUPPORTED_FORMATS:
            ext = fmt.lower()
            if ext == "jpeg":
                ext = "jpg"
            format_combo.addItem(f"{fmt} (*.{ext})", fmt)
        form.addRow("저장 포맷:", format_combo)
        layout.addLayout(form)

        # 확인/취소 버튼
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # 선택된 파일 인덱스 수집
        selected_indices = [i for i, cb in enumerate(checkboxes) if cb.isChecked()]
        if not selected_indices:
            QMessageBox.information(self, "일괄 내보내기", "선택된 파일이 없습니다.")
            return

        chosen_format = format_combo.currentData()
        ext = chosen_format.lower()
        if ext == "jpeg":
            ext = "jpg"

        # 저장 폴더 선택
        folder = QFileDialog.getExistingDirectory(self, "일괄 내보내기 폴더 선택")
        if not folder:
            return

        # 일괄 내보내기 진행
        total = len(selected_indices)
        progress = QProgressDialog("일괄 내보내기 중...", "취소", 0, total, self)
        progress.setWindowTitle("일괄 내보내기")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)

        exported_count = 0
        errors: List[str] = []

        for order, slot_index in enumerate(selected_indices):
            if progress.wasCanceled():
                break
            progress.setValue(order)

            slot = self._file_slots[slot_index]
            try:
                composite = self._render_slot_to_image(slot)
                original_name = Path(slot.path).stem
                order_number = order + 1
                filename = f"{order_number}_modified_{original_name}.{ext}"
                save_path = str(Path(folder) / filename)
                self._handler.save(composite, save_path, format=chosen_format)
                exported_count += 1
            except Exception as e:
                errors.append(f"{Path(slot.path).name}: {e}")

        progress.setValue(total)

        if errors:
            error_msg = "\n".join(errors)
            QMessageBox.warning(
                self,
                "일괄 내보내기 완료",
                f"{exported_count}개 파일 내보내기 완료.\n\n실패한 파일:\n{error_msg}",
            )
        else:
            QMessageBox.information(
                self,
                "일괄 내보내기 완료",
                f"{exported_count}개 파일을 '{folder}'에 내보냈습니다.",
            )
        self._status_label.setText(f"일괄 내보내기 완료: {exported_count}개 파일")

    def _render_slot_to_image(self, slot: _FileSlot) -> Image.Image:
        """파일 슬롯의 이미지에 도형을 합성하여 반환합니다."""
        from PIL import ImageDraw
        from src.core.shape_manager import ShapeType

        result = slot.image.copy()
        draw = ImageDraw.Draw(result, "RGBA")
        inv = (1.0 / slot.scale) if slot.scale > 0 else 1.0

        for shape in slot.shape_manager.shapes:
            x = int(shape.x * inv)
            y = int(shape.y * inv)
            w = int(shape.width * inv)
            h = int(shape.height * inv)
            width = max(1, int(shape.pen_width * inv))
            box = [x, y, x + w, y + h]
            fill = shape.fill_color or None
            if shape.shape_type == ShapeType.RECTANGLE:
                draw.rectangle(box, fill=fill, outline=shape.pen_color, width=width)
            elif shape.shape_type == ShapeType.ELLIPSE:
                draw.ellipse(box, fill=fill, outline=shape.pen_color, width=width)

        return result

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
        """도형 선택/해제 시 툴바의 속성 컨트롤을 해당 도형의 값으로 동기화합니다."""
        if shape is not None:
            self._toolbar.sync_to_shape(shape.pen_color, shape.pen_width, shape.fill_color)

    def _on_zoom_changed(self, zoom: float) -> None:
        self._toolbar.update_zoom_label(zoom)
        if 0 <= self._current_slot_index < len(self._file_slots):
            self._file_slots[self._current_slot_index].zoom = zoom

    def _on_props_changed(self, pen_color: str, pen_width: int, fill_color: Optional[str]) -> None:
        self._canvas.pen_color = pen_color
        self._canvas.pen_width = pen_width
        self._canvas.fill_color = fill_color
        # 선택된 도형이 있으면 실시간으로 스타일 반영
        self._canvas.apply_style_to_selected(pen_color, pen_width, fill_color)
