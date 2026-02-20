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


def _pil_to_pixmap(image: Image.Image) -> QPixmap:
    rgba = image.convert("RGBA")
    data = rgba.tobytes("raw", "RGBA")
    qimg = QImage(data, rgba.width, rgba.height, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg)


class Canvas(QWidget):
    # 도형 선택/해제 시 발생 (선택된 Shape 또는 None)
    selection_changed = pyqtSignal(object)

    def __init__(self, shape_manager: ShapeManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._shape_manager = shape_manager
        self._image: Optional[Image.Image] = None
        self._pixmap: Optional[QPixmap] = None
        self._handler = ImageHandler()
        self._scale: float = 1.0

        # 그리기 모드 상태
        self._draw_start: Optional[QPoint] = None
        self._draw_preview: Optional[QRect] = None

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
        self.setStyleSheet(f"background: {CANVAS_BG_COLOR};")

    # ── 읽기 전용 속성 ──────────────────────────────────────────
    @property
    def image(self) -> Optional[Image.Image]:
        return self._image

    @property
    def scale(self) -> float:
        return self._scale

    # ── 선택 모드 ───────────────────────────────────────────────
    @property
    def select_mode(self) -> bool:
        return self._select_mode

    @select_mode.setter
    def select_mode(self, value: bool) -> None:
        self._select_mode = value
        if not value:
            self._selected_index = None
            self._resize_handle = None
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

    # ── 이미지 로드 ─────────────────────────────────────────────
    def load_image(self, path: str, max_size: Optional[Tuple[int, int]] = None) -> None:
        self._image = self._handler.load(path)
        self._scale = self._calc_scale(self._image.size, max_size)
        display_w = int(self._image.width * self._scale)
        display_h = int(self._image.height * self._scale)
        display_img = (
            self._image.resize((display_w, display_h), Image.LANCZOS)
            if self._scale != 1.0 else self._image
        )
        self._pixmap = _pil_to_pixmap(display_img)
        self._selected_index = None
        self._resize_handle = None
        self.setFixedSize(display_w, display_h)
        self.update()

    def set_slot(
        self,
        image: Image.Image,
        scale: float,
        pixmap: QPixmap,
        shape_manager: ShapeManager,
    ) -> None:
        """멀티 파일 전환: 캔버스를 다른 파일 슬롯으로 교체합니다."""
        self._image = image
        self._scale = scale
        self._pixmap = pixmap
        self._shape_manager = shape_manager
        self._selected_index = None
        self._draw_start = None
        self._draw_preview = None
        self._is_dragging = False
        self._resize_handle = None
        self.setFixedSize(pixmap.width(), pixmap.height())
        self.update()

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

    def clear_shapes(self) -> None:
        self._shape_manager.clear()
        self._selected_index = None
        self.update()

    # ── 도형 합성 내보내기 ──────────────────────────────────────
    def render_to_image(self) -> Optional[Image.Image]:
        """모든 도형을 원본 이미지에 합성한 PIL Image를 반환합니다."""
        if self._image is None:
            return None
        result = self._image.copy()
        draw = ImageDraw.Draw(result, "RGBA")
        inv = (1.0 / self._scale) if self._scale > 0 else 1.0
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
        """선택된 도형의 8개 리사이즈 핸들 QRect를 반환합니다."""
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

    def _get_handle_at(self, pos: QPoint) -> Optional[str]:
        """pos 위치에 해당하는 핸들 이름('nw'~'se')을 반환합니다. 없으면 None."""
        if self._selected_index is None:
            return None
        shapes = self._shape_manager.shapes
        if self._selected_index >= len(shapes):
            return None
        shape = shapes[self._selected_index]
        for name, rect in self._handle_rects(shape).items():
            # 클릭 감도를 위해 3px 여백 추가
            hit = QRect(rect.x() - 3, rect.y() - 3, rect.width() + 6, rect.height() + 6)
            if hit.contains(pos):
                return name
        return None

    # ── 페인트 ──────────────────────────────────────────────────
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        if self._pixmap:
            painter.drawPixmap(0, 0, self._pixmap)
        for i, shape in enumerate(self._shape_manager.shapes):
            self._draw_shape(painter, shape)
            if i == self._selected_index:
                self._draw_selection_indicator(painter, shape)
        if self._draw_preview:
            self._draw_preview_shape(painter)

    def _draw_shape(self, painter: QPainter, shape: Shape) -> None:
        pen = QPen(QColor(shape.pen_color), shape.pen_width)
        painter.setPen(pen)
        painter.setBrush(QColor(shape.fill_color) if shape.fill_color else Qt.BrushStyle.NoBrush)
        rect = QRect(shape.x, shape.y, shape.width, shape.height)
        if shape.shape_type == ShapeType.RECTANGLE:
            painter.drawRect(rect)
        elif shape.shape_type == ShapeType.ELLIPSE:
            painter.drawEllipse(rect)

    def _draw_selection_indicator(self, painter: QPainter, shape: Shape) -> None:
        """선택된 도형 주위에 점선 테두리와 8개 리사이즈 핸들을 표시합니다."""
        # 점선 테두리
        pen = QPen(QColor("#0080FF"), 1, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        rect = QRect(shape.x - 3, shape.y - 3, shape.width + 6, shape.height + 6)
        painter.drawRect(rect)
        # 8개 핸들 (흰 배경 + 파란 테두리)
        painter.setPen(QPen(QColor("#0080FF"), 1))
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        for handle_rect in self._handle_rects(shape).values():
            painter.drawRect(handle_rect)

    def _draw_preview_shape(self, painter: QPainter) -> None:
        pen = QPen(QColor(self._pen_color), self._pen_width, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self._current_shape_type == ShapeType.RECTANGLE:
            painter.drawRect(self._draw_preview)
        elif self._current_shape_type == ShapeType.ELLIPSE:
            painter.drawEllipse(self._draw_preview)

    # ── 마우스 이벤트 ────────────────────────────────────────────
    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position().toPoint()
        if self._select_mode:
            # 리사이즈 핸들 우선 확인 (선택된 도형이 있을 때)
            handle = self._get_handle_at(pos)
            if handle:
                self._resize_handle = handle
                self._is_dragging = False
            else:
                self._resize_handle = None
                self._handle_select_press(pos)
        else:
            self._draw_start = pos

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
        pos = event.position().toPoint()
        if self._select_mode:
            if self._resize_handle is not None and self._selected_index is not None:
                self._handle_resize_move(pos)
            elif self._is_dragging and self._selected_index is not None:
                self._handle_select_move(pos)
        elif self._draw_start:
            self._draw_preview = QRect(self._draw_start, pos).normalized()
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

        # 'n'/'s'/'w'/'e' 문자 포함 여부로 방향 판단
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
        if self._select_mode:
            self._is_dragging = False
            self._resize_handle = None
            return
        if self._draw_start:
            pos = event.position().toPoint()
            rect = QRect(self._draw_start, pos).normalized()
            if rect.width() > 2 and rect.height() > 2:
                self._shape_manager.add(Shape(
                    shape_type=self._current_shape_type,
                    x=rect.x(), y=rect.y(),
                    width=rect.width(), height=rect.height(),
                    pen_color=self._pen_color,
                    pen_width=self._pen_width,
                    fill_color=self._fill_color,
                ))
            self._draw_start = None
            self._draw_preview = None
            self.update()

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
