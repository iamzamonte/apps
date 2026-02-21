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
from src.core.shape_manager import ShapeManager, Shape
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
        self._pre_crop_slot: Optional[_FileSlot] = None
        self._pre_crop_slot_index: int = -1
        self._pre_save_slots: dict[int, _FileSlot] = {}
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
        self._toolbar.reset_requested.connect(self._reset_all)
        self._toolbar.open_requested.connect(self._open_file)
        self._toolbar.save_requested.connect(self._save_file)
        self._toolbar.save_undo_requested.connect(self._undo_save)
        self._toolbar.export_requested.connect(self._export_file)
        self._toolbar.batch_export_requested.connect(self._batch_export)
        self._toolbar.tool_changed.connect(self._on_tool_changed)
        self._toolbar.properties_changed.connect(self._on_props_changed)
        self._toolbar.zoom_in_requested.connect(self._canvas.zoom_in)
        self._toolbar.zoom_out_requested.connect(self._canvas.zoom_out)
        self._toolbar.zoom_reset_requested.connect(self._canvas.zoom_reset)
        self._toolbar.crop_mode_toggled.connect(self._on_crop_mode_toggled)
        self._toolbar.crop_undo_requested.connect(self._undo_crop)
        self._canvas.zoom_changed.connect(self._on_zoom_changed)
        self._canvas.crop_performed.connect(self._on_crop_performed)
        self._canvas.crop_cancelled.connect(self._toolbar.exit_crop_mode)
        self._explorer.file_selected.connect(self._switch_to_file)
        self._explorer.file_delete_requested.connect(self._delete_file)
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
        # crop 모드 해제
        if self._canvas.crop_mode:
            self._canvas.crop_mode = False
            self._toolbar.exit_crop_mode()
        # 되돌리기 히스토리 초기화
        self._pre_crop_slot = None
        self._toolbar.set_crop_undo_enabled(False)
        # 현재 슬롯의 줌 레벨 저장
        if 0 <= self._current_slot_index < len(self._file_slots):
            self._file_slots[self._current_slot_index].zoom = self._canvas.zoom
        self._current_slot_index = index
        slot = self._file_slots[index]
        self._canvas.set_slot(slot.image, slot.scale, slot.pixmap, slot.shape_manager, slot.zoom)
        self._explorer.set_current(index)
        self._toolbar.set_save_undo_enabled(index in self._pre_save_slots)
        self._status_label.setText(slot.path.split("/")[-1])

    def _delete_file(self, index: int) -> None:
        """파일 탐색기에서 파일을 삭제합니다."""
        if not (0 <= index < len(self._file_slots)):
            return
        # 되돌리기 히스토리 초기화
        self._pre_crop_slot = None
        self._toolbar.set_crop_undo_enabled(False)
        # 저장 되돌리기: 삭제된 인덱스 제거 + 인덱스 재조정
        new_pre_save: dict[int, _FileSlot] = {}
        for k, v in self._pre_save_slots.items():
            if k < index:
                new_pre_save[k] = v
            elif k > index:
                new_pre_save[k - 1] = v
        self._pre_save_slots = new_pre_save

        was_current = (index == self._current_slot_index)

        # 불변 방식으로 슬롯 제거
        self._file_slots = [*self._file_slots[:index], *self._file_slots[index + 1:]]
        self._explorer.remove_file(index)

        if not self._file_slots:
            # 모든 파일이 삭제됨
            self._current_slot_index = -1
            self._canvas._shape_manager = self._default_sm
            self._canvas.clear_image()
            self._status_label.setText("Ready")
            return

        if was_current:
            # 현재 파일 삭제: 같은 위치(또는 마지막)로 전환
            new_index = min(index, len(self._file_slots) - 1)
            self._current_slot_index = -1  # force re-switch
            self._switch_to_file(new_index)
        elif index < self._current_slot_index:
            # 현재 파일 이전 삭제: 인덱스 조정
            self._current_slot_index -= 1

    def _reset_all(self) -> None:
        """모든 작업을 초기화하고 빈 상태로 되돌립니다."""
        if self._canvas.crop_mode:
            self._canvas.crop_mode = False
            self._toolbar.exit_crop_mode()
        self._file_slots = []
        self._current_slot_index = -1
        self._pre_crop_slot = None
        self._pre_save_slots = {}
        self._toolbar.set_crop_undo_enabled(False)
        self._toolbar.set_save_undo_enabled(False)
        self._explorer.clear()
        self._canvas.clear_image()
        self._canvas._shape_manager = self._default_sm
        self._status_label.setText("Ready")

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

    def _save_file(self) -> None:
        """현재 편집 중인 파일을 원본 경로에 덮어쓰기 저장합니다."""
        idx = self._current_slot_index
        if not (0 <= idx < len(self._file_slots)):
            QMessageBox.information(self, "저장", "먼저 이미지를 불러오세요.")
            return
        slot = self._file_slots[idx]
        try:
            # 되돌리기용 이전 상태 저장
            self._pre_save_slots[idx] = slot
            # 도형 합성 이미지 생성 및 저장
            composite = self._render_slot_to_image(slot)
            self._handler.save(composite, slot.path)
            # 저장된 이미지로 슬롯 교체 (도형은 이미 합성됨)
            vp = self._scroll.viewport().size()
            max_size = (max(vp.width() - 10, 400), max(vp.height() - 10, 300))
            new_scale = self._canvas._calc_scale(composite.size, max_size)
            display_w = int(composite.width * new_scale)
            display_h = int(composite.height * new_scale)
            display_img = (
                composite.resize((display_w, display_h), Image.LANCZOS)
                if new_scale != 1.0 else composite
            )
            new_pixmap = _pil_to_pixmap(display_img)
            new_slot = _FileSlot(
                path=slot.path,
                image=composite,
                scale=new_scale,
                pixmap=new_pixmap,
                shape_manager=ShapeManager(),
                zoom=1.0,
            )
            self._file_slots = [
                *self._file_slots[:idx], new_slot, *self._file_slots[idx + 1:]
            ]
            # 캔버스/썸네일 갱신
            self._canvas.set_slot(
                new_slot.image, new_slot.scale, new_slot.pixmap,
                new_slot.shape_manager, new_slot.zoom,
            )
            thumb = self._make_thumbnail(composite)
            self._explorer.update_thumbnail(idx, thumb)
            self._toolbar.set_save_undo_enabled(True)
            self._status_label.setText(f"저장 완료: {slot.path.split('/')[-1]}")
        except Exception as e:
            QMessageBox.warning(self, "저장 실패", f"이미지를 저장할 수 없습니다.\n{e}")

    def _undo_save(self) -> None:
        """저장 되돌리기: 저장 전 상태로 복원합니다."""
        idx = self._current_slot_index
        if idx not in self._pre_save_slots:
            return
        old_slot = self._pre_save_slots[idx]
        try:
            # 원본 이미지를 파일에 다시 저장
            self._handler.save(old_slot.image, old_slot.path)
        except Exception as e:
            QMessageBox.warning(self, "되돌리기 실패", f"파일을 복원할 수 없습니다.\n{e}")
            return
        # 슬롯 복원
        self._file_slots = [
            *self._file_slots[:idx], old_slot, *self._file_slots[idx + 1:]
        ]
        self._canvas.set_slot(
            old_slot.image, old_slot.scale, old_slot.pixmap,
            old_slot.shape_manager, old_slot.zoom,
        )
        thumb = self._make_thumbnail(old_slot.image)
        self._explorer.update_thumbnail(idx, thumb)
        del self._pre_save_slots[idx]
        self._toolbar.set_save_undo_enabled(idx in self._pre_save_slots)
        self._status_label.setText(f"저장 되돌리기 완료: {old_slot.path.split('/')[-1]}")

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
        self._canvas.crop_mode = False
        if shape_type is None:
            self._canvas.select_mode = True
        else:
            self._canvas.select_mode = False
            self._canvas.current_shape_type = shape_type

    def _on_crop_mode_toggled(self, active: bool) -> None:
        """자르기 모드 전환."""
        self._canvas.crop_mode = active
        if active:
            self._status_label.setText(
                "자르기 영역을 조절한 뒤 Enter로 확정, Esc로 취소"
            )

    def _on_crop_performed(self, crop_data: dict) -> None:
        """자르기 완료 후 이미지·슬롯을 갱신합니다."""
        if not (0 <= self._current_slot_index < len(self._file_slots)):
            return

        cropped_image = crop_data['image']
        crop_box = crop_data['crop_box']  # (left, top, right, bottom) 원본 px
        crop_bs = crop_data['crop_box_base_scale']  # (left_bs, top_bs)

        slot = self._file_slots[self._current_slot_index]
        # 되돌리기용 이전 상태 저장
        self._pre_crop_slot = slot
        self._pre_crop_slot_index = self._current_slot_index
        crop_left_bs, crop_top_bs = crop_bs
        crop_w_bs = int((crop_box[2] - crop_box[0]) * slot.scale)
        crop_h_bs = int((crop_box[3] - crop_box[1]) * slot.scale)

        # 도형 좌표 조정: 크롭 원점 기준으로 이동, 영역 밖 도형 제거
        new_sm = ShapeManager()
        for shape in slot.shape_manager.shapes:
            new_x = shape.x - crop_left_bs
            new_y = shape.y - crop_top_bs
            if (new_x + shape.width > 0 and new_y + shape.height > 0
                    and new_x < crop_w_bs and new_y < crop_h_bs):
                clamped_x = max(0, new_x)
                clamped_y = max(0, new_y)
                clamped_w = min(new_x + shape.width, crop_w_bs) - clamped_x
                clamped_h = min(new_y + shape.height, crop_h_bs) - clamped_y
                if clamped_w > 2 and clamped_h > 2:
                    new_sm.add(Shape(
                        shape_type=shape.shape_type,
                        x=clamped_x, y=clamped_y,
                        width=clamped_w, height=clamped_h,
                        pen_color=shape.pen_color,
                        pen_width=shape.pen_width,
                        fill_color=shape.fill_color,
                    ))

        # 새 스케일/픽스맵 계산
        vp = self._scroll.viewport().size()
        max_size = (max(vp.width() - 10, 400), max(vp.height() - 10, 300))
        new_scale = self._canvas._calc_scale(cropped_image.size, max_size)
        display_w = int(cropped_image.width * new_scale)
        display_h = int(cropped_image.height * new_scale)
        display_img = (
            cropped_image.resize((display_w, display_h), Image.LANCZOS)
            if new_scale != 1.0 else cropped_image
        )
        new_pixmap = _pil_to_pixmap(display_img)

        # 불변 방식으로 슬롯 교체
        new_slot = _FileSlot(
            path=slot.path,
            image=cropped_image,
            scale=new_scale,
            pixmap=new_pixmap,
            shape_manager=new_sm,
            zoom=1.0,
        )
        self._file_slots = [
            *self._file_slots[:self._current_slot_index],
            new_slot,
            *self._file_slots[self._current_slot_index + 1:]
        ]

        # 썸네일 갱신
        thumb = self._make_thumbnail(cropped_image)
        self._explorer.update_thumbnail(self._current_slot_index, thumb)

        # 캔버스 교체 + 자르기 모드 해제
        self._canvas.set_slot(
            new_slot.image, new_slot.scale, new_slot.pixmap,
            new_slot.shape_manager, new_slot.zoom
        )
        self._canvas.crop_mode = False
        self._toolbar.exit_crop_mode()
        self._toolbar.set_crop_undo_enabled(True)

    def _undo_crop(self) -> None:
        """자르기 되돌리기: 직전 크롭 이전 상태로 복원합니다."""
        if self._pre_crop_slot is None:
            return
        idx = self._pre_crop_slot_index
        if not (0 <= idx < len(self._file_slots)):
            return
        old_slot = self._pre_crop_slot
        self._file_slots = [
            *self._file_slots[:idx], old_slot,
            *self._file_slots[idx + 1:]
        ]
        thumb = self._make_thumbnail(old_slot.image)
        self._explorer.update_thumbnail(idx, thumb)
        if idx == self._current_slot_index:
            self._canvas.set_slot(
                old_slot.image, old_slot.scale, old_slot.pixmap,
                old_slot.shape_manager, old_slot.zoom,
            )
        self._pre_crop_slot = None
        self._toolbar.set_crop_undo_enabled(False)

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
