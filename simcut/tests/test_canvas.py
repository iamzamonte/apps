import pytest
from PIL import Image
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QMouseEvent
from src.ui.canvas import Canvas, _pil_to_pixmap
from src.core.shape_manager import ShapeManager, Shape, ShapeType


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def sample_image(tmp_path):
    img_path = tmp_path / "test.png"
    Image.new("RGB", (200, 150), (0, 255, 0)).save(str(img_path))
    return str(img_path)


def test_canvas_initial_image_is_none(app):
    canvas = Canvas(ShapeManager())
    assert canvas.image is None


def test_canvas_load_image(app, sample_image):
    canvas = Canvas(ShapeManager())
    canvas.load_image(sample_image)
    assert canvas.image is not None


def test_canvas_image_size_after_load(app, tmp_path):
    img_path = tmp_path / "test.png"
    Image.new("RGB", (320, 240), (0, 0, 255)).save(str(img_path))
    canvas = Canvas(ShapeManager())
    canvas.load_image(str(img_path))
    assert canvas.image.size == (320, 240)


def test_canvas_clear_shapes(app):
    manager = ShapeManager()
    canvas = Canvas(manager)
    manager.add(Shape(ShapeType.RECTANGLE, 0, 0, 50, 50, "#f00", 2, None))
    canvas.clear_shapes()
    assert len(manager.shapes) == 0


def test_pil_to_pixmap_returns_pixmap(app):
    img = Image.new("RGB", (50, 50), (128, 128, 128))
    pixmap = _pil_to_pixmap(img)
    assert not pixmap.isNull()
    assert pixmap.width() == 50
    assert pixmap.height() == 50


def test_canvas_default_pen_settings(app):
    from src.utils.constants import DEFAULT_PEN_COLOR, DEFAULT_PEN_WIDTH
    canvas = Canvas(ShapeManager())
    assert canvas.pen_color == DEFAULT_PEN_COLOR
    assert canvas.pen_width == DEFAULT_PEN_WIDTH
    assert canvas.fill_color is None


def test_canvas_shape_type_default_is_rectangle(app):
    canvas = Canvas(ShapeManager())
    assert canvas.current_shape_type == ShapeType.RECTANGLE


def test_canvas_pen_settings_can_be_updated(app):
    canvas = Canvas(ShapeManager())
    canvas.pen_color = "#00FF00"
    canvas.pen_width = 5
    canvas.fill_color = "#0000FF"
    assert canvas.pen_color == "#00FF00"
    assert canvas.pen_width == 5
    assert canvas.fill_color == "#0000FF"


def test_canvas_mouse_draw_adds_shape(app, sample_image):
    manager = ShapeManager()
    canvas = Canvas(manager)
    canvas.load_image(sample_image)

    # 마우스 클릭+드래그+릴리즈로 도형 생성 시뮬레이션
    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(10, 10),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    release = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(80, 70),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mousePressEvent(press)
    canvas.mouseReleaseEvent(release)
    assert len(manager.shapes) == 1


def test_canvas_mouse_draw_ellipse(app, sample_image):
    manager = ShapeManager()
    canvas = Canvas(manager)
    canvas.load_image(sample_image)
    canvas.current_shape_type = ShapeType.ELLIPSE

    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(20, 20),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    release = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(90, 80),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mousePressEvent(press)
    canvas.mouseReleaseEvent(release)
    assert manager.shapes[0].shape_type == ShapeType.ELLIPSE


def test_canvas_too_small_drag_does_not_add_shape(app, sample_image):
    manager = ShapeManager()
    canvas = Canvas(manager)
    canvas.load_image(sample_image)

    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(10, 10),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    release = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(11, 11),  # 2px 이하 → 무시
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier
    )
    canvas.mousePressEvent(press)
    canvas.mouseReleaseEvent(release)
    assert len(manager.shapes) == 0


# ── 이미지 스케일 테스트 ────────────────────────────────────────

def test_load_image_with_max_size_scales_down(app, tmp_path):
    img_path = tmp_path / "large.png"
    Image.new("RGB", (2000, 1000), (0, 0, 0)).save(str(img_path))
    canvas = Canvas(ShapeManager())
    canvas.load_image(str(img_path), max_size=(800, 600))
    assert canvas.width() <= 800
    assert canvas.height() <= 600
    assert canvas.scale < 1.0


def test_load_image_scale_maintains_aspect_ratio(app, tmp_path):
    img_path = tmp_path / "wide.png"
    Image.new("RGB", (1000, 500), (0, 0, 0)).save(str(img_path))
    canvas = Canvas(ShapeManager())
    canvas.load_image(str(img_path), max_size=(400, 400))
    # 가로 2:1 비율 유지 확인
    assert abs(canvas.width() / canvas.height() - 2.0) < 0.1


def test_load_image_no_max_size_uses_original(app, tmp_path):
    img_path = tmp_path / "small.png"
    Image.new("RGB", (300, 200), (0, 0, 0)).save(str(img_path))
    canvas = Canvas(ShapeManager())
    canvas.load_image(str(img_path))
    assert canvas.scale == 1.0
    assert canvas.width() == 300
    assert canvas.height() == 200


# ── 선택/이동 모드 테스트 ───────────────────────────────────────

def test_select_mode_toggle(app):
    canvas = Canvas(ShapeManager())
    assert canvas.select_mode is False
    canvas.select_mode = True
    assert canvas.select_mode is True


def test_select_mode_off_clears_selection(app, sample_image):
    manager = ShapeManager()
    canvas = Canvas(manager)
    canvas.load_image(sample_image)
    manager.add(Shape(ShapeType.RECTANGLE, 10, 10, 80, 60, "#f00", 2, None))
    canvas.select_mode = True
    # 도형 클릭으로 선택
    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(50, 40),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mousePressEvent(press)
    assert canvas._selected_index == 0
    # 선택 모드 해제 시 선택 초기화
    canvas.select_mode = False
    assert canvas._selected_index is None


def test_shape_selection_by_click(app, sample_image):
    manager = ShapeManager()
    canvas = Canvas(manager)
    canvas.load_image(sample_image)
    manager.add(Shape(ShapeType.RECTANGLE, 20, 20, 60, 40, "#f00", 2, None))
    canvas.select_mode = True
    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(40, 35),  # 도형 내부 클릭
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mousePressEvent(press)
    assert canvas._selected_index == 0


def test_click_outside_shape_deselects(app, sample_image):
    manager = ShapeManager()
    canvas = Canvas(manager)
    canvas.load_image(sample_image)
    manager.add(Shape(ShapeType.RECTANGLE, 20, 20, 40, 40, "#f00", 2, None))
    canvas.select_mode = True
    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(5, 5),  # 도형 바깥 클릭
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mousePressEvent(press)
    assert canvas._selected_index is None


def test_shape_moves_on_drag(app, sample_image):
    manager = ShapeManager()
    canvas = Canvas(manager)
    canvas.load_image(sample_image)
    manager.add(Shape(ShapeType.RECTANGLE, 20, 20, 60, 40, "#f00", 2, None))
    canvas.select_mode = True
    # 클릭
    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(40, 35),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mousePressEvent(press)
    # 이동
    move = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(100, 90),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mouseMoveEvent(move)
    shape = manager.shapes[0]
    assert shape.x != 20 or shape.y != 20  # 위치가 변경됨


# ── 리사이즈 핸들 테스트 ────────────────────────────────────────

def test_resize_se_handle_enlarges_shape(app, sample_image):
    """SE 핸들 드래그 시 너비·높이 증가."""
    manager = ShapeManager()
    canvas = Canvas(manager)
    canvas.load_image(sample_image)
    manager.add(Shape(ShapeType.RECTANGLE, 20, 20, 60, 40, "#f00", 2, None))
    canvas.select_mode = True
    canvas._selected_index = 0  # 이미 선택된 상태로 시작

    # SE 핸들 위치: x+w=80, y+h=60 → QRect(76,56,8,8)
    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(80, 60),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mousePressEvent(press)
    assert canvas._resize_handle == 'se'

    move = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(100, 80),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mouseMoveEvent(move)
    shape = manager.shapes[0]
    assert shape.width == 80   # 100 - 20
    assert shape.height == 60  # 80 - 20


def test_resize_nw_handle_changes_origin(app, sample_image):
    """NW 핸들 드래그 시 원점 이동 + 크기 변경."""
    manager = ShapeManager()
    canvas = Canvas(manager)
    canvas.load_image(sample_image)
    manager.add(Shape(ShapeType.RECTANGLE, 40, 40, 60, 40, "#f00", 2, None))
    canvas.select_mode = True
    canvas._selected_index = 0

    # NW 핸들: x=40, y=40 → QRect(36,36,8,8)
    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(40, 40),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mousePressEvent(press)
    assert canvas._resize_handle == 'nw'

    move = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(30, 30),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mouseMoveEvent(move)
    shape = manager.shapes[0]
    assert shape.x == 30
    assert shape.y == 30
    assert shape.width == 70   # 40 + 60 - 30
    assert shape.height == 50  # 40 + 40 - 30


def test_resize_e_handle_changes_width_only(app, sample_image):
    """E 핸들 드래그 시 너비만 변경되고 원점은 유지."""
    manager = ShapeManager()
    canvas = Canvas(manager)
    canvas.load_image(sample_image)
    manager.add(Shape(ShapeType.RECTANGLE, 10, 10, 50, 50, "#f00", 2, None))
    canvas.select_mode = True
    canvas._selected_index = 0

    # E 핸들: x+w=60, cy=35 → QRect(56,31,8,8)
    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(60, 35),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mousePressEvent(press)
    assert canvas._resize_handle == 'e'

    move = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(90, 35),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mouseMoveEvent(move)
    shape = manager.shapes[0]
    assert shape.x == 10       # x 변경 없음
    assert shape.y == 10       # y 변경 없음
    assert shape.width == 80   # 90 - 10
    assert shape.height == 50  # 높이 변경 없음


def test_resize_release_clears_handle(app, sample_image):
    """마우스 릴리즈 후 resize_handle이 None으로 초기화."""
    manager = ShapeManager()
    canvas = Canvas(manager)
    canvas.load_image(sample_image)
    manager.add(Shape(ShapeType.RECTANGLE, 20, 20, 60, 40, "#f00", 2, None))
    canvas.select_mode = True
    canvas._selected_index = 0

    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(80, 60),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mousePressEvent(press)
    assert canvas._resize_handle == 'se'

    release = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(100, 80),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mouseReleaseEvent(release)
    assert canvas._resize_handle is None


# ── set_slot 테스트 ──────────────────────────────────────────────

# ── 선택 도형 스타일 실시간 반영 테스트 ─────────────────────────

def test_apply_style_updates_selected_shape(app, sample_image):
    """선택된 도형에 apply_style_to_selected 호출 시 속성이 변경된다."""
    manager = ShapeManager()
    canvas = Canvas(manager)
    canvas.load_image(sample_image)
    manager.add(Shape(ShapeType.RECTANGLE, 10, 10, 80, 60, "#f00", 2, None))
    canvas._selected_index = 0

    canvas.apply_style_to_selected("#0000FF", 5, "#FFFF00")

    shape = manager.shapes[0]
    assert shape.pen_color == "#0000FF"
    assert shape.pen_width == 5
    assert shape.fill_color == "#FFFF00"


def test_apply_style_no_selection_does_nothing(app, sample_image):
    """선택된 도형이 없을 때는 아무 변화가 없다."""
    manager = ShapeManager()
    canvas = Canvas(manager)
    canvas.load_image(sample_image)
    manager.add(Shape(ShapeType.RECTANGLE, 10, 10, 80, 60, "#f00", 2, None))
    # _selected_index 는 None (기본값)

    canvas.apply_style_to_selected("#0000FF", 5, None)

    shape = manager.shapes[0]
    assert shape.pen_color == "#f00"  # 변경 없음
    assert shape.pen_width == 2


def test_apply_style_preserves_geometry(app, sample_image):
    """스타일 변경 시 도형의 위치·크기는 유지된다."""
    manager = ShapeManager()
    canvas = Canvas(manager)
    canvas.load_image(sample_image)
    manager.add(Shape(ShapeType.ELLIPSE, 15, 25, 70, 50, "#f00", 2, None))
    canvas._selected_index = 0

    canvas.apply_style_to_selected("#00FF00", 3, None)

    shape = manager.shapes[0]
    assert shape.x == 15
    assert shape.y == 25
    assert shape.width == 70
    assert shape.height == 50


def test_selection_changed_signal_emitted_on_click(app, sample_image):
    """도형 클릭 시 selection_changed 시그널이 Shape로 발생한다."""
    manager = ShapeManager()
    canvas = Canvas(manager)
    canvas.load_image(sample_image)
    manager.add(Shape(ShapeType.RECTANGLE, 20, 20, 60, 40, "#f00", 2, None))
    canvas.select_mode = True

    received = []
    canvas.selection_changed.connect(received.append)

    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(40, 35),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mousePressEvent(press)

    assert len(received) == 1
    assert received[0] is not None
    assert received[0].pen_color == "#f00"


def test_selection_changed_signal_emitted_on_deselect(app, sample_image):
    """도형 바깥 클릭 시 selection_changed 시그널이 None으로 발생한다."""
    manager = ShapeManager()
    canvas = Canvas(manager)
    canvas.load_image(sample_image)
    manager.add(Shape(ShapeType.RECTANGLE, 20, 20, 40, 40, "#f00", 2, None))
    canvas.select_mode = True
    canvas._selected_index = 0

    received = []
    canvas.selection_changed.connect(received.append)

    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(5, 5),  # 도형 바깥
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mousePressEvent(press)

    assert len(received) == 1
    assert received[0] is None


def test_set_slot_switches_image_and_shapes(app, tmp_path):
    """set_slot 호출 시 이미지·도형 매니저가 교체된다."""
    from src.ui.canvas import _pil_to_pixmap
    from PIL import Image as PILImage

    manager1 = ShapeManager()
    manager2 = ShapeManager()
    manager2.add(Shape(ShapeType.ELLIPSE, 5, 5, 30, 30, "#00f", 1, None))

    canvas = Canvas(manager1)

    img2 = PILImage.new("RGB", (100, 80), (0, 255, 0))
    pixmap2 = _pil_to_pixmap(img2)
    canvas.set_slot(img2, 1.0, pixmap2, manager2)

    assert canvas.image is img2
    assert canvas._shape_manager is manager2
    assert len(canvas._shape_manager.shapes) == 1


# ── 줌 기능 테스트 ────────────────────────────────────────────

def test_canvas_initial_zoom_is_one(app):
    canvas = Canvas(ShapeManager())
    assert canvas.zoom == 1.0


def test_canvas_zoom_in(app, sample_image):
    canvas = Canvas(ShapeManager())
    canvas.load_image(sample_image)
    canvas.zoom_in()
    assert canvas.zoom > 1.0


def test_canvas_zoom_out(app, sample_image):
    canvas = Canvas(ShapeManager())
    canvas.load_image(sample_image)
    canvas.zoom_out()
    assert canvas.zoom < 1.0


def test_canvas_zoom_reset(app, sample_image):
    canvas = Canvas(ShapeManager())
    canvas.load_image(sample_image)
    canvas.zoom_in()
    canvas.zoom_in()
    assert canvas.zoom > 1.0
    canvas.zoom_reset()
    assert abs(canvas.zoom - 1.0) < 0.01


def test_canvas_zoom_clamped_min(app, sample_image):
    from src.ui.canvas import MIN_ZOOM
    canvas = Canvas(ShapeManager())
    canvas.load_image(sample_image)
    canvas.set_zoom(0.01)
    assert canvas.zoom >= MIN_ZOOM


def test_canvas_zoom_clamped_max(app, sample_image):
    from src.ui.canvas import MAX_ZOOM
    canvas = Canvas(ShapeManager())
    canvas.load_image(sample_image)
    canvas.set_zoom(100.0)
    assert canvas.zoom <= MAX_ZOOM


def test_canvas_zoom_changes_widget_size(app, sample_image):
    canvas = Canvas(ShapeManager())
    canvas.load_image(sample_image)
    w_before = canvas.width()
    canvas.set_zoom(2.0)
    assert canvas.width() > w_before


def test_canvas_zoom_changed_signal(app, sample_image):
    canvas = Canvas(ShapeManager())
    canvas.load_image(sample_image)
    received = []
    canvas.zoom_changed.connect(received.append)
    canvas.zoom_in()
    assert len(received) == 1
    assert received[0] > 1.0


def test_set_slot_restores_zoom(app):
    from PIL import Image as PILImage
    manager = ShapeManager()
    canvas = Canvas(manager)
    img = PILImage.new("RGB", (100, 80), (255, 0, 0))
    pixmap = _pil_to_pixmap(img)
    canvas.set_slot(img, 1.0, pixmap, manager, zoom=2.0)
    assert abs(canvas.zoom - 2.0) < 0.01


def test_canvas_scale_unaffected_by_zoom(app, sample_image):
    """scale 속성은 base_scale을 반환하며 줌 영향을 받지 않는다."""
    canvas = Canvas(ShapeManager())
    canvas.load_image(sample_image)
    base = canvas.scale
    canvas.set_zoom(2.0)
    assert canvas.scale == base


# ── clear_image 테스트 ─────────────────────────────────────────

def test_canvas_clear_image(app, sample_image):
    canvas = Canvas(ShapeManager())
    canvas.load_image(sample_image)
    assert canvas.image is not None
    canvas.clear_image()
    assert canvas.image is None


# ── 자르기 모드 테스트 ─────────────────────────────────────────

def test_canvas_crop_mode_default_false(app):
    canvas = Canvas(ShapeManager())
    assert canvas.crop_mode is False


def test_canvas_crop_mode_toggle(app):
    canvas = Canvas(ShapeManager())
    canvas.crop_mode = True
    assert canvas.crop_mode is True
    assert canvas.select_mode is False


def test_crop_mode_clears_select_mode(app):
    canvas = Canvas(ShapeManager())
    canvas.select_mode = True
    canvas.crop_mode = True
    assert canvas.select_mode is False


def test_select_mode_clears_crop_mode(app):
    canvas = Canvas(ShapeManager())
    canvas.crop_mode = True
    canvas.select_mode = True
    assert canvas.crop_mode is False


def test_crop_mode_initializes_crop_rect(app, sample_image):
    """자르기 모드 진입 시 crop_rect가 전체 이미지 크기로 초기화된다."""
    canvas = Canvas(ShapeManager())
    canvas.load_image(sample_image)
    canvas.crop_mode = True
    assert canvas._crop_rect is not None
    assert canvas._crop_rect.width() == canvas._pixmap.width()
    assert canvas._crop_rect.height() == canvas._pixmap.height()


def test_crop_performed_signal(app, sample_image):
    """Enter 키로 자르기 확정 시 crop_performed 시그널이 발생한다."""
    from PyQt6.QtGui import QKeyEvent
    from PyQt6.QtCore import QEvent
    canvas = Canvas(ShapeManager())
    canvas.load_image(sample_image)
    canvas.crop_mode = True
    received = []
    canvas.crop_performed.connect(received.append)
    key_event = QKeyEvent(
        QEvent.Type.KeyPress, Qt.Key.Key_Return,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.keyPressEvent(key_event)
    assert len(received) == 1
    assert 'image' in received[0]
    assert 'crop_box' in received[0]


def test_crop_too_small_ignored(app, sample_image):
    """너무 작은 영역은 크롭하지 않는다."""
    from PyQt6.QtGui import QKeyEvent
    from PyQt6.QtCore import QEvent, QRect
    canvas = Canvas(ShapeManager())
    canvas.load_image(sample_image)
    canvas.crop_mode = True
    canvas._crop_rect = QRect(10, 10, 1, 1)
    received = []
    canvas.crop_performed.connect(received.append)
    key_event = QKeyEvent(
        QEvent.Type.KeyPress, Qt.Key.Key_Return,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.keyPressEvent(key_event)
    assert len(received) == 0


def test_crop_no_image_ignored(app):
    """이미지 없이 크롭 시도하면 무시된다."""
    from PyQt6.QtGui import QKeyEvent
    from PyQt6.QtCore import QEvent
    canvas = Canvas(ShapeManager())
    canvas.crop_mode = True
    assert canvas._crop_rect is None
    received = []
    canvas.crop_performed.connect(received.append)
    key_event = QKeyEvent(
        QEvent.Type.KeyPress, Qt.Key.Key_Return,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.keyPressEvent(key_event)
    assert len(received) == 0


def test_crop_esc_cancels(app, sample_image):
    """Esc 키로 자르기 모드를 취소한다."""
    from PyQt6.QtGui import QKeyEvent
    from PyQt6.QtCore import QEvent
    canvas = Canvas(ShapeManager())
    canvas.load_image(sample_image)
    canvas.crop_mode = True
    assert canvas.crop_mode is True
    cancelled = []
    canvas.crop_cancelled.connect(lambda: cancelled.append(True))
    key_event = QKeyEvent(
        QEvent.Type.KeyPress, Qt.Key.Key_Escape,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.keyPressEvent(key_event)
    assert canvas.crop_mode is False
    assert canvas._crop_rect is None
    assert len(cancelled) == 1


def test_crop_handle_resize(app, sample_image):
    """크롭 핸들 드래그로 영역 크기가 변경된다."""
    canvas = Canvas(ShapeManager())
    canvas.load_image(sample_image)
    canvas.crop_mode = True
    original_width = canvas._crop_rect.width()
    # E(오른쪽) 핸들 위치에서 마우스 프레스
    e_handle_x = canvas._crop_rect.x() + canvas._crop_rect.width()
    e_handle_y = (canvas._crop_rect.y()
                  + canvas._crop_rect.height() // 2)
    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(e_handle_x, e_handle_y),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mousePressEvent(press)
    assert canvas._crop_handle == 'e'
    # 왼쪽으로 드래그하여 폭 줄이기
    new_x = e_handle_x - 50
    move = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(new_x, e_handle_y),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mouseMoveEvent(move)
    assert canvas._crop_rect.width() < original_width
