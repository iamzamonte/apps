from __future__ import annotations
from typing import Optional, Tuple, Dict
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPixmap, QColor, QPen, QBrush, QImage
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PIL import Image, ImageDraw
from src.core.shape_manager import ShapeManager, Shape, ShapeType
from src.core.image_handler import ImageHandler
from src.utils.constants import (
    DEFAULT_PEN_COLOR, DEFAULT_PEN_WIDTH, CANVAS_BG_COLOR,
    MIN_PEN_WIDTH, MAX_PEN_WIDTH
)

# 리사이즈 핸들 크기 (px)
HANDLE_SIZE = 8
# 도형 최소 크기 (리사이즈 하한)
MIN_SHAPE_SIZE = 4
# 자르기 핸들
CROP_HANDLE_SIZE = 10
MIN_CROP_SIZE = 20
# 줌 범위
MIN_ZOOM = 0.25
MAX_ZOOM = 4.0
ZOOM_STEP = 1.15  # 휠 한 칸당 15% 변경


def _pil_to_pixmap(image: Image.Image) -> QPixmap:
    rgba = image.convert("RGBA")
    data = rgba.tobytes("raw", "RGBA")
    qimg = QImage(data, rgba.width, rgba.height, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg)


class Canvas(QWidget):
    # 도형 선택/해제 시 발생 (선택된 Shape 또는 None)
    selection_changed = pyqtSignal(object)
    # 줌 레벨 변경 시 발생 (float: 줌 비율)
    zoom_changed = pyqtSignal(float)
    # 자르기 완료 시 발생 (dict: image, crop_box, crop_box_base_scale)
    crop_performed = pyqtSignal(object)
    # 자르기 모드 취소 (Esc) 시 발생
    crop_cancelled = pyqtSignal()

    def __init__(self, shape_manager: ShapeManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._shape_manager = shape_manager
        self._image: Optional[Image.Image] = None
        self._pixmap: Optional[QPixmap] = None
        self._handler = ImageHandler()
        self._base_scale: float = 1.0
        self._zoom: float = 1.0

        # 그리기 모드 상태
        self._draw_start: Optional[QPoint] = None
        self._draw_preview: Optional[QRect] = None

        # 자르기 모드 상태
        self._crop_mode: bool = False
        self._crop_rect: Optional[QRect] = None
        self._crop_handle: Optional[str] = None
        self._crop_move_start: Optional[QPoint] = None

        # 선택/이동/리사이즈 모드 상태
        self._select_mode: bool = False
        self._selected_index: Optional[int] = None
        self._drag_offset: QPoint = QPoint(0, 0)
        self._is_dragging: bool = False
        self._resize_handle: Optional[str] = None  # 'nw','n','ne','w','e','sw','s','se'

        # 도형 속성 (private + property 검증)
        self._current_shape_type: ShapeType = ShapeType.RECTANGLE
        self._pen_color: str = DEFAULT_PEN_COLOR
        self._pen_width: int = DEFAULT_PEN_WIDTH
        self._fill_color: Optional[str] = None

        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setStyleSheet(f"background: {CANVAS_BG_COLOR};")

    # ── 읽기 전용 속성 ──────────────────────────────────────────
    @property
    def image(self) -> Optional[Image.Image]:
        return self._image

    @property
    def scale(self) -> float:
        """내보내기용 base scale (줌 미포함)."""
        return self._base_scale

    @property
    def zoom(self) -> float:
        return self._zoom

    # ── 선택 모드 ───────────────────────────────────────────────
    @property
    def select_mode(self) -> bool:
        return self._select_mode

    @select_mode.setter
    def select_mode(self, value: bool) -> None:
        self._select_mode = value
        if value:
            self._crop_mode = False
            self._crop_rect = None
            self._crop_handle = None
            self._crop_move_start = None
        if not value:
            self._selected_index = None
            self._resize_handle = None
        self.update()

    # ── 자르기 모드 ──────────────────────────────────────────────
    @property
    def crop_mode(self) -> bool:
        return self._crop_mode

    @crop_mode.setter
    def crop_mode(self, value: bool) -> None:
        self._crop_mode = value
        if value and self._pixmap:
            self._crop_rect = QRect(0, 0, self._pixmap.width(), self._pixmap.height())
        else:
            self._crop_rect = None
        self._crop_handle = None
        self._crop_move_start = None
        self._draw_start = None
        if value:
            self._select_mode = False
            self._selected_index = None
        self.update()

    # ── 도형 도구 속성 (검증 포함) ──────────────────────────────
    @property
    def current_shape_type(self) -> ShapeType:
        return self._current_shape_type

    @current_shape_type.setter
    def current_shape_type(self, value: ShapeType) -> None:
        if not isinstance(value, ShapeType):
            raise ValueError(f"Expected ShapeType, got {type(value)}")
        self._current_shape_type = value

    @property
    def pen_color(self) -> str:
        return self._pen_color

    @pen_color.setter
    def pen_color(self, value: str) -> None:
        if not isinstance(value, str) or not value.startswith("#"):
            raise ValueError(f"pen_color must be a hex color string (e.g. '#FF0000'), got '{value}'")
        self._pen_color = value

    @property
    def pen_width(self) -> int:
        return self._pen_width

    @pen_width.setter
    def pen_width(self, value: int) -> None:
        if not isinstance(value, int) or not (MIN_PEN_WIDTH <= value <= MAX_PEN_WIDTH):
            raise ValueError(f"pen_width must be between {MIN_PEN_WIDTH} and {MAX_PEN_WIDTH}, got {value}")
        self._pen_width = value

    @property
    def fill_color(self) -> Optional[str]:
        return self._fill_color

    @fill_color.setter
    def fill_color(self, value: Optional[str]) -> None:
        if value is not None and (not isinstance(value, str) or not value.startswith("#")):
            raise ValueError(f"fill_color must be a hex color string or None, got '{value}'")
        self._fill_color = value

    # ── 줌 ────────────────────────────────────────────────────────
    def set_zoom(self, zoom: float) -> None:
        """줌 레벨을 설정하고 디스플레이를 갱신합니다."""
        clamped = max(MIN_ZOOM, min(zoom, MAX_ZOOM))
        if abs(clamped - self._zoom) < 0.001:
            return
        self._zoom = clamped
        self._rebuild_display()
        self.zoom_changed.emit(self._zoom)

    def zoom_in(self) -> None:
        self.set_zoom(self._zoom * ZOOM_STEP)

    def zoom_out(self) -> None:
        self.set_zoom(self._zoom / ZOOM_STEP)

    def zoom_reset(self) -> None:
        self.set_zoom(1.0)

    def _rebuild_display(self) -> None:
        """현재 줌 레벨에 맞게 디스플레이 픽스맵을 재생성합니다."""
        if self._image is None:
            return
        eff = self._base_scale * self._zoom
        display_w = max(1, int(self._image.width * eff))
        display_h = max(1, int(self._image.height * eff))
        display_img = self._image.resize((display_w, display_h), Image.LANCZOS)
        self._pixmap = _pil_to_pixmap(display_img)
        self.setFixedSize(display_w, display_h)
        self.update()

    # ── 좌표 변환 헬퍼 ────────────────────────────────────────────
    def _to_shape_space(self, display_pos: QPoint) -> QPoint:
        """디스플레이(줌 적용) 좌표 → 도형(base_scale) 좌표."""
        z = self._zoom if self._zoom > 0 else 1.0
        return QPoint(int(display_pos.x() / z), int(display_pos.y() / z))

    def _to_display(self, val: int) -> int:
        """도형 좌표 값 → 디스플레이 좌표 값."""
        return int(val * self._zoom)

    # ── 이미지 로드 ─────────────────────────────────────────────
    def load_image(self, path: str, max_size: Optional[Tuple[int, int]] = None) -> None:
        self._image = self._handler.load(path)
        self._base_scale = self._calc_scale(self._image.size, max_size)
        self._zoom = 1.0
        display_w = int(self._image.width * self._base_scale)
        display_h = int(self._image.height * self._base_scale)
        display_img = (
            self._image.resize((display_w, display_h), Image.LANCZOS)
            if self._base_scale != 1.0 else self._image
        )
        self._pixmap = _pil_to_pixmap(display_img)
        self._selected_index = None
        self._resize_handle = None
        self.setFixedSize(display_w, display_h)
        self.update()
        self.zoom_changed.emit(self._zoom)

    def set_slot(
        self,
        image: Image.Image,
        scale: float,
        pixmap: QPixmap,
        shape_manager: ShapeManager,
        zoom: float = 1.0,
    ) -> None:
        """멀티 파일 전환: 캔버스를 다른 파일 슬롯으로 교체합니다."""
        self._image = image
        self._base_scale = scale
        self._zoom = zoom
        self._shape_manager = shape_manager
        self._selected_index = None
        self._draw_start = None
        self._draw_preview = None
        self._is_dragging = False
        self._resize_handle = None
        self._crop_mode = False
        self._crop_rect = None
        self._crop_handle = None
        self._crop_move_start = None
        if abs(zoom - 1.0) < 0.001:
            self._pixmap = pixmap
            self.setFixedSize(pixmap.width(), pixmap.height())
        else:
            self._rebuild_display()
        self.update()
        self.zoom_changed.emit(self._zoom)

    def _calc_scale(
        self,
        image_size: Tuple[int, int],
        max_size: Optional[Tuple[int, int]],
    ) -> float:
        if not max_size:
            return 1.0
        orig_w, orig_h = image_size
        max_w, max_h = max_size
        if orig_w <= 0 or orig_h <= 0:
            return 1.0
        return min(max_w / orig_w, max_h / orig_h, 1.0)  # 원본보다 크게 확대하지 않음

    def clear_image(self) -> None:
        """이미지를 제거하고 초기 상태로 되돌립니다."""
        self._image = None
        self._pixmap = None
        self._selected_index = None
        self._draw_start = None
        self._draw_preview = None
        self._is_dragging = False
        self._resize_handle = None
        self._zoom = 1.0
        self.setFixedSize(0, 0)
        self.update()
        self.zoom_changed.emit(self._zoom)

    def clear_shapes(self) -> None:
        self._shape_manager.clear()
        self._selected_index = None
        self.update()

    def delete_selected(self) -> None:
        """선택된 도형을 삭제합니다."""
        if self._selected_index is None:
            return
        if self._selected_index >= len(self._shape_manager.shapes):
            return
        self._shape_manager.remove(self._selected_index)
        self._selected_index = None
        self._resize_handle = None
        self.selection_changed.emit(None)
        self.update()

    # ── 도형 합성 내보내기 ──────────────────────────────────────
    def render_to_image(self) -> Optional[Image.Image]:
        """모든 도형을 원본 이미지에 합성한 PIL Image를 반환합니다."""
        if self._image is None:
            return None
        result = self._image.copy()
        draw = ImageDraw.Draw(result, "RGBA")
        inv = (1.0 / self._base_scale) if self._base_scale > 0 else 1.0
        for shape in self._shape_manager.shapes:
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

    def apply_style_to_selected(
        self,
        pen_color: str,
        pen_width: int,
        fill_color: Optional[str],
    ) -> None:
        """선택된 도형의 선 색상·굵기·채움 색상을 실시간으로 변경합니다."""
        if self._selected_index is None:
            return
        shapes = self._shape_manager.shapes
        if self._selected_index >= len(shapes):
            return
        old = shapes[self._selected_index]
        new_shape = Shape(
            shape_type=old.shape_type,
            x=old.x, y=old.y,
            width=old.width, height=old.height,
            pen_color=pen_color,
            pen_width=pen_width,
            fill_color=fill_color,
        )
        self._shape_manager.replace(self._selected_index, new_shape)
        self.update()

    # ── 리사이즈 핸들 ────────────────────────────────────────────
    def _handle_rects(self, shape: Shape) -> Dict[str, QRect]:
        """선택된 도형의 8개 리사이즈 핸들 QRect (base_scale 좌표)를 반환합니다."""
        x, y, w, h = shape.x, shape.y, shape.width, shape.height
        hs = HANDLE_SIZE // 2
        cx = x + w // 2
        cy = y + h // 2
        return {
            'nw': QRect(x - hs,      y - hs,      HANDLE_SIZE, HANDLE_SIZE),
            'n':  QRect(cx - hs,     y - hs,      HANDLE_SIZE, HANDLE_SIZE),
            'ne': QRect(x + w - hs,  y - hs,      HANDLE_SIZE, HANDLE_SIZE),
            'w':  QRect(x - hs,      cy - hs,     HANDLE_SIZE, HANDLE_SIZE),
            'e':  QRect(x + w - hs,  cy - hs,     HANDLE_SIZE, HANDLE_SIZE),
            'sw': QRect(x - hs,      y + h - hs,  HANDLE_SIZE, HANDLE_SIZE),
            's':  QRect(cx - hs,     y + h - hs,  HANDLE_SIZE, HANDLE_SIZE),
            'se': QRect(x + w - hs,  y + h - hs,  HANDLE_SIZE, HANDLE_SIZE),
        }

    def _get_handle_at(self, shape_pos: QPoint) -> Optional[str]:
        """shape_pos(base_scale 좌표)에 해당하는 핸들 이름을 반환합니다."""
        if self._selected_index is None:
            return None
        shapes = self._shape_manager.shapes
        if self._selected_index >= len(shapes):
            return None
        shape = shapes[self._selected_index]
        for name, rect in self._handle_rects(shape).items():
            # 클릭 감도를 위해 3px 여백 추가
            hit = QRect(rect.x() - 3, rect.y() - 3, rect.width() + 6, rect.height() + 6)
            if hit.contains(shape_pos):
                return name
        return None

    # ── 페인트 ──────────────────────────────────────────────────
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        if self._pixmap:
            painter.drawPixmap(0, 0, self._pixmap)
        z = self._zoom
        for i, shape in enumerate(self._shape_manager.shapes):
            self._draw_shape(painter, shape, z)
            if i == self._selected_index:
                self._draw_selection_indicator(painter, shape, z)
        if self._draw_preview:
            self._draw_preview_shape(painter, z)
        if self._crop_rect:
            self._draw_crop_preview(painter)

    def _draw_shape(self, painter: QPainter, shape: Shape, z: float) -> None:
        pen = QPen(QColor(shape.pen_color), max(1, shape.pen_width * z))
        painter.setPen(pen)
        painter.setBrush(QColor(shape.fill_color) if shape.fill_color else Qt.BrushStyle.NoBrush)
        rect = QRect(
            self._to_display(shape.x), self._to_display(shape.y),
            self._to_display(shape.width), self._to_display(shape.height),
        )
        if shape.shape_type == ShapeType.RECTANGLE:
            painter.drawRect(rect)
        elif shape.shape_type == ShapeType.ELLIPSE:
            painter.drawEllipse(rect)

    def _draw_selection_indicator(self, painter: QPainter, shape: Shape, z: float) -> None:
        """선택된 도형 주위에 점선 테두리와 8개 리사이즈 핸들을 표시합니다."""
        dx, dy = self._to_display(shape.x), self._to_display(shape.y)
        dw, dh = self._to_display(shape.width), self._to_display(shape.height)
        # 점선 테두리
        pen = QPen(QColor("#0080FF"), 1, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRect(dx - 3, dy - 3, dw + 6, dh + 6))
        # 8개 핸들 (흰 배경 + 파란 테두리) — 화면 고정 크기
        painter.setPen(QPen(QColor("#0080FF"), 1))
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        for handle_rect in self._handle_rects(shape).values():
            display_rect = QRect(
                self._to_display(handle_rect.x()),
                self._to_display(handle_rect.y()),
                HANDLE_SIZE, HANDLE_SIZE,
            )
            painter.drawRect(display_rect)

    def _draw_preview_shape(self, painter: QPainter, z: float) -> None:
        pen = QPen(QColor(self._pen_color), max(1, self._pen_width * z), Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # _draw_preview는 이미 디스플레이 좌표로 저장됨
        if self._current_shape_type == ShapeType.RECTANGLE:
            painter.drawRect(self._draw_preview)
        elif self._current_shape_type == ShapeType.ELLIPSE:
            painter.drawEllipse(self._draw_preview)

    # ── 마우스 이벤트 ────────────────────────────────────────────
    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        display_pos = event.position().toPoint()
        pos = self._to_shape_space(display_pos)
        if self._crop_mode:
            if self._crop_rect is None:
                return
            handle = self._get_crop_handle_at(display_pos)
            if handle:
                self._crop_handle = handle
            elif self._crop_rect.contains(display_pos):
                self._crop_move_start = display_pos
            return
        if self._select_mode:
            handle = self._get_handle_at(pos)
            if handle:
                self._resize_handle = handle
                self._is_dragging = False
            else:
                self._resize_handle = None
                self._handle_select_press(pos)
        else:
            self._draw_start = display_pos

    def _handle_select_press(self, pos: QPoint) -> None:
        shapes = self._shape_manager.shapes
        for i in range(len(shapes) - 1, -1, -1):  # 위에 그려진 도형 우선
            if QRect(shapes[i].x, shapes[i].y, shapes[i].width, shapes[i].height).contains(pos):
                self._selected_index = i
                self._drag_offset = QPoint(pos.x() - shapes[i].x, pos.y() - shapes[i].y)
                self._is_dragging = True
                self.selection_changed.emit(shapes[i])
                self.update()
                return
        self._selected_index = None
        self._is_dragging = False
        self.selection_changed.emit(None)
        self.update()

    def mouseMoveEvent(self, event) -> None:
        display_pos = event.position().toPoint()
        pos = self._to_shape_space(display_pos)
        if self._crop_mode:
            if self._crop_handle and self._crop_rect:
                self._resize_crop_rect(display_pos)
                self.update()
            elif self._crop_move_start and self._crop_rect:
                dx = display_pos.x() - self._crop_move_start.x()
                dy = display_pos.y() - self._crop_move_start.y()
                self._crop_rect.translate(dx, dy)
                self._crop_move_start = display_pos
                self.update()
            return
        if self._select_mode:
            if self._resize_handle is not None and self._selected_index is not None:
                self._handle_resize_move(pos)
            elif self._is_dragging and self._selected_index is not None:
                self._handle_select_move(pos)
        elif self._draw_start:
            self._draw_preview = QRect(self._draw_start, display_pos).normalized()
            self.update()

    def _handle_select_move(self, pos: QPoint) -> None:
        shapes = self._shape_manager.shapes
        if self._selected_index is None or self._selected_index >= len(shapes):
            return
        old = shapes[self._selected_index]
        new_shape = Shape(
            shape_type=old.shape_type,
            x=pos.x() - self._drag_offset.x(),
            y=pos.y() - self._drag_offset.y(),
            width=old.width,
            height=old.height,
            pen_color=old.pen_color,
            pen_width=old.pen_width,
            fill_color=old.fill_color,
        )
        self._shape_manager.replace(self._selected_index, new_shape)
        self.update()

    def _handle_resize_move(self, pos: QPoint) -> None:
        """리사이즈 핸들 드래그로 도형 크기/위치 변경."""
        shapes = self._shape_manager.shapes
        if self._selected_index is None or self._selected_index >= len(shapes):
            return
        old = shapes[self._selected_index]
        x, y, w, h = old.x, old.y, old.width, old.height
        handle = self._resize_handle

        if 'n' in handle:
            new_h = y + h - pos.y()
            if new_h > MIN_SHAPE_SIZE:
                y = pos.y()
                h = new_h
        if 's' in handle:
            new_h = pos.y() - y
            if new_h > MIN_SHAPE_SIZE:
                h = new_h
        if 'w' in handle:
            new_w = x + w - pos.x()
            if new_w > MIN_SHAPE_SIZE:
                x = pos.x()
                w = new_w
        if 'e' in handle:
            new_w = pos.x() - x
            if new_w > MIN_SHAPE_SIZE:
                w = new_w

        new_shape = Shape(
            shape_type=old.shape_type,
            x=x, y=y, width=w, height=h,
            pen_color=old.pen_color,
            pen_width=old.pen_width,
            fill_color=old.fill_color,
        )
        self._shape_manager.replace(self._selected_index, new_shape)
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._crop_mode:
            self._crop_handle = None
            self._crop_move_start = None
            return
        if self._select_mode:
            self._is_dragging = False
            self._resize_handle = None
            return
        if self._draw_start:
            display_pos = event.position().toPoint()
            display_rect = QRect(self._draw_start, display_pos).normalized()
            # 디스플레이 좌표 → 도형(base_scale) 좌표
            shape_rect = QRect(
                self._to_shape_space(QPoint(display_rect.x(), display_rect.y())).x(),
                self._to_shape_space(QPoint(display_rect.x(), display_rect.y())).y(),
                int(display_rect.width() / self._zoom) if self._zoom > 0 else display_rect.width(),
                int(display_rect.height() / self._zoom) if self._zoom > 0 else display_rect.height(),
            )
            if shape_rect.width() > 2 and shape_rect.height() > 2:
                self._shape_manager.add(Shape(
                    shape_type=self._current_shape_type,
                    x=shape_rect.x(), y=shape_rect.y(),
                    width=shape_rect.width(), height=shape_rect.height(),
                    pen_color=self._pen_color,
                    pen_width=self._pen_width,
                    fill_color=self._fill_color,
                ))
            self._draw_start = None
            self._draw_preview = None
            self.update()

    # ── 자르기 핸들 ────────────────────────────────────────────────
    def _crop_handle_rects(self) -> Dict[str, QRect]:
        """크롭 영역의 8개 핸들 QRect (디스플레이 좌표)."""
        r = self._crop_rect
        if r is None:
            return {}
        hs = CROP_HANDLE_SIZE // 2
        cx = r.x() + r.width() // 2
        cy = r.y() + r.height() // 2
        rr = r.x() + r.width()
        rb = r.y() + r.height()
        s = CROP_HANDLE_SIZE
        return {
            'nw': QRect(r.x() - hs, r.y() - hs, s, s),
            'n':  QRect(cx - hs,    r.y() - hs, s, s),
            'ne': QRect(rr - hs,    r.y() - hs, s, s),
            'w':  QRect(r.x() - hs, cy - hs,    s, s),
            'e':  QRect(rr - hs,    cy - hs,    s, s),
            'sw': QRect(r.x() - hs, rb - hs,    s, s),
            's':  QRect(cx - hs,    rb - hs,    s, s),
            'se': QRect(rr - hs,    rb - hs,    s, s),
        }

    def _get_crop_handle_at(self, pos: QPoint) -> Optional[str]:
        """클릭 위치에 해당하는 크롭 핸들 이름을 반환합니다."""
        for name, rect in self._crop_handle_rects().items():
            hit = QRect(
                rect.x() - 3, rect.y() - 3,
                rect.width() + 6, rect.height() + 6,
            )
            if hit.contains(pos):
                return name
        return None

    def _resize_crop_rect(self, pos: QPoint) -> None:
        """크롭 핸들 드래그로 영역 크기를 변경합니다."""
        if self._crop_rect is None or self._crop_handle is None:
            return
        handle = self._crop_handle
        x, y = self._crop_rect.x(), self._crop_rect.y()
        right = x + self._crop_rect.width()
        bottom = y + self._crop_rect.height()

        if 'n' in handle:
            new_y = pos.y()
            if bottom - new_y >= MIN_CROP_SIZE:
                y = new_y
        if 's' in handle:
            new_bottom = pos.y()
            if new_bottom - y >= MIN_CROP_SIZE:
                bottom = new_bottom
        if 'w' in handle:
            new_x = pos.x()
            if right - new_x >= MIN_CROP_SIZE:
                x = new_x
        if 'e' in handle:
            new_right = pos.x()
            if new_right - x >= MIN_CROP_SIZE:
                right = new_right

        self._crop_rect = QRect(x, y, right - x, bottom - y)

    # ── 자르기 ──────────────────────────────────────────────────
    def _apply_crop(self, display_rect: QRect) -> None:
        """크롭 영역을 적용하여 이미지를 잘라냅니다."""
        if self._image is None:
            return
        eff = self._base_scale * self._zoom
        if eff <= 0:
            return
        # 디스플레이 좌표 → 원본 픽셀 좌표
        left = max(0, int(display_rect.x() / eff))
        top = max(0, int(display_rect.y() / eff))
        right = min(self._image.width, int((display_rect.x() + display_rect.width()) / eff))
        bottom = min(self._image.height, int((display_rect.y() + display_rect.height()) / eff))
        if right - left < 2 or bottom - top < 2:
            return
        crop_left_bs = int(left * self._base_scale)
        crop_top_bs = int(top * self._base_scale)
        self.crop_performed.emit({
            'image': self._image.crop((left, top, right, bottom)),
            'crop_box': (left, top, right, bottom),
            'crop_box_base_scale': (crop_left_bs, crop_top_bs),
        })

    def _draw_crop_preview(self, painter: QPainter) -> None:
        """자르기 영역 미리보기: 영역 외부를 어둡게, 테두리와 핸들을 표시합니다."""
        cr = self._crop_rect
        if cr is None:
            return
        full = self.rect()
        overlay = QColor(0, 0, 0, 80)
        # 상단
        painter.fillRect(QRect(0, 0, full.width(), cr.top()), overlay)
        # 하단
        painter.fillRect(QRect(0, cr.bottom(), full.width(), full.height() - cr.bottom()), overlay)
        # 좌측 (상단/하단 사이)
        painter.fillRect(QRect(0, cr.top(), cr.left(), cr.height()), overlay)
        # 우측
        painter.fillRect(QRect(cr.right(), cr.top(), full.width() - cr.right(), cr.height()), overlay)
        # 점선 테두리
        pen = QPen(QColor("#FFFFFF"), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(cr)
        # 8개 핸들 (흰 배경 + 파란 테두리)
        painter.setPen(QPen(QColor("#0080FF"), 1))
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        for handle_rect in self._crop_handle_rects().values():
            painter.drawRect(handle_rect)

    # ── 키보드 이벤트 ──────────────────────────────────────────────
    def keyPressEvent(self, event) -> None:
        if self._crop_mode:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if self._crop_rect and self._image:
                    self._apply_crop(self._crop_rect)
            elif event.key() == Qt.Key.Key_Escape:
                self.crop_mode = False
                self.crop_cancelled.emit()
            return
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected()
        else:
            super().keyPressEvent(event)

    # ── 마우스 휠 (줌) ────────────────────────────────────────────
    def wheelEvent(self, event) -> None:
        if self._image is None:
            return
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom_in()
        elif delta < 0:
            self.zoom_out()

    # ── 드래그 & 드롭 ────────────────────────────────────────────
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if urls:
            try:
                self.load_image(urls[0].toLocalFile())
            except Exception:
                pass
