# simcut Phase 1 MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Python + PyQt6 기반 Mac OS 사진 편집 앱 MVP 구현 (이미지 불러오기/내보내기, 도형 추가, 포맷 변환, Undo/Redo)

**Architecture:** MVC 패턴 적용. `core/`는 Model (이미지·도형 데이터), `ui/`는 View (렌더링), `main_window.py`는 Controller (이벤트·레이어 연결). 이미지 처리는 Pillow, GUI는 PyQt6.

**Tech Stack:** Python 3.11+, PyQt6, Pillow, pytest, pytest-qt, PyInstaller

---

## Task 1: 프로젝트 구조 & 가상환경 세팅

**Files:**
- Create: `.venv/` (가상환경)
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `src/ui/__init__.py`
- Create: `src/core/__init__.py`
- Create: `src/utils/__init__.py`
- Create: `tests/__init__.py`

**Step 1: 가상환경 생성**

```bash
cd /Users/montecarlo/Downloads/2_AREA/apps/simcut
python3 -m venv .venv
source .venv/bin/activate
```

Expected: `(.venv)` 프롬프트 표시

**Step 2: 의존성 설치**

```bash
pip install PyQt6 Pillow PyInstaller pytest pytest-qt
pip freeze > requirements.txt
```

Expected: `requirements.txt` 생성됨

**Step 3: 디렉토리 & `__init__.py` 생성**

```bash
mkdir -p src/ui src/core src/utils tests assets/icons
touch src/__init__.py src/ui/__init__.py src/core/__init__.py src/utils/__init__.py tests/__init__.py
```

**Step 4: 설치 확인**

```bash
python -c "import PyQt6; import PIL; print('OK')"
```

Expected: `OK`

**Step 5: Commit**

```bash
git init
git add .
git commit -m "chore: 프로젝트 초기 구조 & 가상환경 세팅"
```

---

## Task 2: 상수 정의 (`utils/constants.py`)

**Files:**
- Create: `src/utils/constants.py`
- Test: `tests/test_constants.py`

**Step 1: 테스트 작성**

```python
# tests/test_constants.py
from src.utils.constants import (
    SUPPORTED_FORMATS, DEFAULT_PEN_WIDTH, DEFAULT_PEN_COLOR,
    DEFAULT_FILL_COLOR, APP_NAME
)

def test_supported_formats_contains_common_types():
    assert "PNG" in SUPPORTED_FORMATS
    assert "JPEG" in SUPPORTED_FORMATS
    assert "WEBP" in SUPPORTED_FORMATS
    assert "BMP" in SUPPORTED_FORMATS

def test_default_pen_width_is_positive():
    assert DEFAULT_PEN_WIDTH > 0
    assert DEFAULT_PEN_WIDTH <= 20

def test_app_name():
    assert APP_NAME == "simcut"
```

**Step 2: 테스트 실패 확인**

```bash
pytest tests/test_constants.py -v
```

Expected: FAIL — `ModuleNotFoundError`

**Step 3: 구현**

```python
# src/utils/constants.py
APP_NAME = "simcut"

SUPPORTED_FORMATS = ["PNG", "JPEG", "WEBP", "BMP"]

OPEN_FILE_FILTER = "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
SAVE_FILE_FILTER = "PNG (*.png);;JPEG (*.jpg *.jpeg);;WebP (*.webp);;BMP (*.bmp)"

DEFAULT_PEN_WIDTH = 2
DEFAULT_PEN_COLOR = "#FF0000"   # 빨강
DEFAULT_FILL_COLOR = None       # 투명 (채움 없음)

MIN_PEN_WIDTH = 1
MAX_PEN_WIDTH = 20

CANVAS_BG_COLOR = "#F0F0F0"
```

**Step 4: 테스트 통과 확인**

```bash
pytest tests/test_constants.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/utils/constants.py tests/test_constants.py
git commit -m "feat: 앱 상수 정의"
```

---

## Task 3: 이미지 핸들러 (`core/image_handler.py`)

**Files:**
- Create: `src/core/image_handler.py`
- Test: `tests/test_image_handler.py`
- Test Asset: `tests/fixtures/sample.png` (테스트용 이미지)

**Step 1: 테스트용 샘플 이미지 생성**

```bash
mkdir -p tests/fixtures
python -c "
from PIL import Image
img = Image.new('RGB', (100, 100), color=(255, 0, 0))
img.save('tests/fixtures/sample.png')
print('sample.png created')
"
```

**Step 2: 테스트 작성**

```python
# tests/test_image_handler.py
import pytest
import os
from pathlib import Path
from src.core.image_handler import ImageHandler

FIXTURE_PATH = Path("tests/fixtures/sample.png")
OUTPUT_PATH = Path("tests/fixtures/output.jpg")

@pytest.fixture(autouse=True)
def cleanup():
    yield
    if OUTPUT_PATH.exists():
        OUTPUT_PATH.unlink()

def test_load_image_returns_pil_image():
    handler = ImageHandler()
    img = handler.load(str(FIXTURE_PATH))
    assert img is not None
    assert img.size == (100, 100)

def test_load_nonexistent_raises_error():
    handler = ImageHandler()
    with pytest.raises(FileNotFoundError):
        handler.load("nonexistent.png")

def test_save_converts_format():
    handler = ImageHandler()
    img = handler.load(str(FIXTURE_PATH))
    handler.save(img, str(OUTPUT_PATH), format="JPEG")
    assert OUTPUT_PATH.exists()

def test_get_image_info():
    handler = ImageHandler()
    img = handler.load(str(FIXTURE_PATH))
    info = handler.get_info(img)
    assert info["width"] == 100
    assert info["height"] == 100
    assert info["mode"] == "RGB"
```

**Step 3: 테스트 실패 확인**

```bash
pytest tests/test_image_handler.py -v
```

Expected: FAIL — `ModuleNotFoundError`

**Step 4: 구현**

```python
# src/core/image_handler.py
from PIL import Image
from pathlib import Path


class ImageHandler:
    def load(self, path: str) -> Image.Image:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Image not found: {path}")
        return Image.open(file_path).copy()

    def save(self, image: Image.Image, path: str, format: str | None = None) -> None:
        file_path = Path(path)
        fmt = format or file_path.suffix.lstrip(".").upper()
        if fmt == "JPG":
            fmt = "JPEG"
        rgb_image = image.convert("RGB") if fmt == "JPEG" else image
        rgb_image.save(str(file_path), format=fmt)

    def get_info(self, image: Image.Image) -> dict:
        return {
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
        }
```

**Step 5: 테스트 통과 확인**

```bash
pytest tests/test_image_handler.py -v
```

Expected: PASS (4/4)

**Step 6: Commit**

```bash
git add src/core/image_handler.py tests/test_image_handler.py tests/fixtures/
git commit -m "feat: 이미지 핸들러 (불러오기/저장/포맷 변환)"
```

---

## Task 4: 도형 데이터 모델 (`core/shape_manager.py`)

**Files:**
- Create: `src/core/shape_manager.py`
- Test: `tests/test_shape_manager.py`

**Step 1: 테스트 작성**

```python
# tests/test_shape_manager.py
import pytest
from src.core.shape_manager import ShapeManager, Shape, ShapeType

def test_add_rectangle():
    manager = ShapeManager()
    shape = Shape(
        shape_type=ShapeType.RECTANGLE,
        x=10, y=20, width=100, height=50,
        pen_color="#FF0000", pen_width=2,
        fill_color=None
    )
    manager.add(shape)
    assert len(manager.shapes) == 1

def test_add_ellipse():
    manager = ShapeManager()
    shape = Shape(
        shape_type=ShapeType.ELLIPSE,
        x=5, y=5, width=80, height=80,
        pen_color="#0000FF", pen_width=3,
        fill_color="#FFFF00"
    )
    manager.add(shape)
    assert manager.shapes[0].fill_color == "#FFFF00"

def test_undo_removes_last_shape():
    manager = ShapeManager()
    shape = Shape(ShapeType.RECTANGLE, 0, 0, 50, 50, "#000", 1, None)
    manager.add(shape)
    manager.undo()
    assert len(manager.shapes) == 0

def test_redo_restores_shape():
    manager = ShapeManager()
    shape = Shape(ShapeType.RECTANGLE, 0, 0, 50, 50, "#000", 1, None)
    manager.add(shape)
    manager.undo()
    manager.redo()
    assert len(manager.shapes) == 1

def test_clear_all():
    manager = ShapeManager()
    manager.add(Shape(ShapeType.RECTANGLE, 0, 0, 10, 10, "#000", 1, None))
    manager.add(Shape(ShapeType.ELLIPSE, 0, 0, 10, 10, "#000", 1, None))
    manager.clear()
    assert len(manager.shapes) == 0
```

**Step 2: 테스트 실패 확인**

```bash
pytest tests/test_shape_manager.py -v
```

Expected: FAIL

**Step 3: 구현**

```python
# src/core/shape_manager.py
from dataclasses import dataclass
from enum import Enum


class ShapeType(Enum):
    RECTANGLE = "rectangle"
    ELLIPSE = "ellipse"


@dataclass
class Shape:
    shape_type: ShapeType
    x: int
    y: int
    width: int
    height: int
    pen_color: str
    pen_width: int
    fill_color: str | None


class ShapeManager:
    def __init__(self):
        self._shapes: list[Shape] = []
        self._undo_stack: list[Shape] = []

    @property
    def shapes(self) -> list[Shape]:
        return list(self._shapes)

    def add(self, shape: Shape) -> None:
        self._shapes = [*self._shapes, shape]
        self._undo_stack.clear()

    def undo(self) -> None:
        if self._shapes:
            removed = self._shapes[-1]
            self._shapes = self._shapes[:-1]
            self._undo_stack = [*self._undo_stack, removed]

    def redo(self) -> None:
        if self._undo_stack:
            restored = self._undo_stack[-1]
            self._undo_stack = self._undo_stack[:-1]
            self._shapes = [*self._shapes, restored]

    def clear(self) -> None:
        self._shapes = []
        self._undo_stack = []
```

**Step 4: 테스트 통과 확인**

```bash
pytest tests/test_shape_manager.py -v
```

Expected: PASS (5/5)

**Step 5: Commit**

```bash
git add src/core/shape_manager.py tests/test_shape_manager.py
git commit -m "feat: 도형 데이터 모델 & Undo/Redo"
```

---

## Task 5: 메인 윈도우 스켈레톤 (`ui/main_window.py`)

**Files:**
- Create: `src/ui/main_window.py`
- Test: `tests/test_main_window.py`

**Step 1: 테스트 작성**

```python
# tests/test_main_window.py
import pytest
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow

@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])

def test_window_title(app):
    window = MainWindow()
    assert window.windowTitle() == "simcut"

def test_window_has_menubar(app):
    window = MainWindow()
    assert window.menuBar() is not None

def test_window_has_statusbar(app):
    window = MainWindow()
    assert window.statusBar() is not None

def test_window_minimum_size(app):
    window = MainWindow()
    assert window.minimumWidth() >= 800
    assert window.minimumHeight() >= 600
```

**Step 2: 테스트 실패 확인**

```bash
pytest tests/test_main_window.py -v
```

Expected: FAIL

**Step 3: 구현**

```python
# src/ui/main_window.py
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QStatusBar, QLabel, QScrollArea
)
from PyQt6.QtCore import Qt
from src.utils.constants import APP_NAME


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(900, 660)
        self._setup_menubar()
        self._setup_toolbar_row()
        self._setup_canvas()
        self._setup_statusbar()

    def _setup_menubar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        edit_menu = menubar.addMenu("Edit")
        view_menu = menubar.addMenu("View")

    def _setup_toolbar_row(self):
        toolbar_widget = QWidget()
        layout = QHBoxLayout(toolbar_widget)
        layout.setContentsMargins(4, 4, 4, 4)
        self._tool_area = QWidget()
        self._prop_area = QWidget()
        layout.addWidget(self._tool_area)
        layout.addStretch()
        layout.addWidget(self._prop_area)

        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(toolbar_widget)
        self._canvas_placeholder = QWidget()
        self._canvas_placeholder.setStyleSheet("background: #F0F0F0;")
        v.addWidget(self._canvas_placeholder, stretch=1)
        self.setCentralWidget(container)

    def _setup_canvas(self):
        pass  # Task 6에서 구현

    def _setup_statusbar(self):
        self.statusBar().showMessage("Ready")
```

**Step 4: 테스트 통과 확인**

```bash
pytest tests/test_main_window.py -v
```

Expected: PASS (4/4)

**Step 5: Commit**

```bash
git add src/ui/main_window.py tests/test_main_window.py
git commit -m "feat: 메인 윈도우 스켈레톤"
```

---

## Task 6: 캔버스 위젯 (`ui/canvas.py`)

**Files:**
- Create: `src/ui/canvas.py`
- Test: `tests/test_canvas.py`

**Step 1: 테스트 작성**

```python
# tests/test_canvas.py
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage
from src.ui.canvas import Canvas
from src.core.shape_manager import ShapeManager

@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])

def test_canvas_initial_image_is_none(app):
    canvas = Canvas(ShapeManager())
    assert canvas.image is None

def test_canvas_load_image(app, tmp_path):
    from PIL import Image
    img_path = tmp_path / "test.png"
    Image.new("RGB", (200, 150), (0, 255, 0)).save(str(img_path))
    canvas = Canvas(ShapeManager())
    canvas.load_image(str(img_path))
    assert canvas.image is not None

def test_canvas_clear_shapes(app):
    from src.core.shape_manager import Shape, ShapeType
    manager = ShapeManager()
    canvas = Canvas(manager)
    shape = Shape(ShapeType.RECTANGLE, 0, 0, 50, 50, "#f00", 2, None)
    manager.add(shape)
    canvas.clear_shapes()
    assert len(manager.shapes) == 0
```

**Step 2: 테스트 실패 확인**

```bash
pytest tests/test_canvas.py -v
```

Expected: FAIL

**Step 3: 구현**

```python
# src/ui/canvas.py
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPixmap, QColor, QPen
from PyQt6.QtCore import Qt, QRect, QPoint
from PIL import Image
from src.core.shape_manager import ShapeManager, Shape, ShapeType
from src.core.image_handler import ImageHandler
from src.utils.constants import (
    DEFAULT_PEN_COLOR, DEFAULT_PEN_WIDTH, CANVAS_BG_COLOR
)


def _pil_to_pixmap(image: Image.Image) -> QPixmap:
    from PyQt6.QtGui import QImage
    rgb = image.convert("RGBA")
    data = rgb.tobytes("raw", "RGBA")
    qimg = QImage(data, rgb.width, rgb.height, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg)


class Canvas(QWidget):
    def __init__(self, shape_manager: ShapeManager, parent=None):
        super().__init__(parent)
        self._shape_manager = shape_manager
        self._image: Image.Image | None = None
        self._pixmap: QPixmap | None = None
        self._handler = ImageHandler()
        self._draw_start: QPoint | None = None
        self._draw_preview: QRect | None = None
        self.current_shape_type = ShapeType.RECTANGLE
        self.pen_color = DEFAULT_PEN_COLOR
        self.pen_width = DEFAULT_PEN_WIDTH
        self.fill_color: str | None = None
        self.setAcceptDrops(True)
        self.setStyleSheet(f"background: {CANVAS_BG_COLOR};")

    @property
    def image(self) -> Image.Image | None:
        return self._image

    def load_image(self, path: str) -> None:
        self._image = self._handler.load(path)
        self._pixmap = _pil_to_pixmap(self._image)
        self.setFixedSize(self._image.width, self._image.height)
        self.update()

    def clear_shapes(self) -> None:
        self._shape_manager.clear()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if self._pixmap:
            painter.drawPixmap(0, 0, self._pixmap)
        for shape in self._shape_manager.shapes:
            self._draw_shape(painter, shape)
        if self._draw_preview:
            self._draw_preview_shape(painter)

    def _draw_shape(self, painter: QPainter, shape: Shape):
        pen = QPen(QColor(shape.pen_color), shape.pen_width)
        painter.setPen(pen)
        if shape.fill_color:
            painter.setBrush(QColor(shape.fill_color))
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
        rect = QRect(shape.x, shape.y, shape.width, shape.height)
        if shape.shape_type == ShapeType.RECTANGLE:
            painter.drawRect(rect)
        elif shape.shape_type == ShapeType.ELLIPSE:
            painter.drawEllipse(rect)

    def _draw_preview_shape(self, painter: QPainter):
        pen = QPen(QColor(self.pen_color), self.pen_width, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self.current_shape_type == ShapeType.RECTANGLE:
            painter.drawRect(self._draw_preview)
        elif self.current_shape_type == ShapeType.ELLIPSE:
            painter.drawEllipse(self._draw_preview)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._draw_start = event.pos()

    def mouseMoveEvent(self, event):
        if self._draw_start:
            self._draw_preview = QRect(self._draw_start, event.pos()).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        if self._draw_start and event.button() == Qt.MouseButton.LeftButton:
            rect = QRect(self._draw_start, event.pos()).normalized()
            if rect.width() > 2 and rect.height() > 2:
                shape = Shape(
                    shape_type=self.current_shape_type,
                    x=rect.x(), y=rect.y(),
                    width=rect.width(), height=rect.height(),
                    pen_color=self.pen_color,
                    pen_width=self.pen_width,
                    fill_color=self.fill_color,
                )
                self._shape_manager.add(shape)
            self._draw_start = None
            self._draw_preview = None
            self.update()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self.load_image(urls[0].toLocalFile())
```

**Step 4: 테스트 통과 확인**

```bash
pytest tests/test_canvas.py -v
```

Expected: PASS (3/3)

**Step 5: Commit**

```bash
git add src/ui/canvas.py tests/test_canvas.py
git commit -m "feat: 캔버스 위젯 (이미지 표시, 도형 그리기, 드래그&드롭)"
```

---

## Task 7: 도구바 & 속성 패널 (`ui/toolbar.py`, `ui/properties.py`)

**Files:**
- Create: `src/ui/toolbar.py`
- Create: `src/ui/properties.py`
- Test: `tests/test_toolbar.py`

**Step 1: 테스트 작성**

```python
# tests/test_toolbar.py
import pytest
from PyQt6.QtWidgets import QApplication
from src.ui.toolbar import Toolbar
from src.ui.properties import PropertiesPanel

@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])

def test_toolbar_has_three_tools(app):
    toolbar = Toolbar()
    assert len(toolbar.tool_buttons) == 3  # 선택, 사각형, 원

def test_properties_panel_default_pen_width(app):
    panel = PropertiesPanel()
    assert panel.pen_width == 2

def test_properties_panel_pen_width_range(app):
    panel = PropertiesPanel()
    panel.set_pen_width(15)
    assert panel.pen_width == 15
```

**Step 2: 테스트 실패 확인**

```bash
pytest tests/test_toolbar.py -v
```

Expected: FAIL

**Step 3: Toolbar 구현**

```python
# src/ui/toolbar.py
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal
from src.core.shape_manager import ShapeType


class Toolbar(QWidget):
    tool_changed = pyqtSignal(object)  # ShapeType or None (선택 도구)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        self.tool_buttons: list[QPushButton] = []
        self._add_tool("→ 선택", None)
        self._add_tool("□ 사각형", ShapeType.RECTANGLE)
        self._add_tool("○ 원", ShapeType.ELLIPSE)

    def _add_tool(self, label: str, shape_type):
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.clicked.connect(lambda _, t=shape_type: self.tool_changed.emit(t))
        self.tool_buttons.append(btn)
        self.layout().addWidget(btn)
```

**Step 4: PropertiesPanel 구현**

```python
# src/ui/properties.py
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QSpinBox, QPushButton, QColorDialog
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor
from src.utils.constants import DEFAULT_PEN_COLOR, DEFAULT_PEN_WIDTH


class PropertiesPanel(QWidget):
    properties_changed = pyqtSignal(str, int, object)  # pen_color, pen_width, fill_color

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        self._pen_color = DEFAULT_PEN_COLOR
        self._fill_color = None

        self._pen_btn = QPushButton("선 색상")
        self._pen_btn.clicked.connect(self._pick_pen_color)
        self._update_btn_color(self._pen_btn, self._pen_color)

        self._fill_btn = QPushButton("채움 색상")
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
    def fill_color(self) -> str | None:
        return self._fill_color

    def set_pen_width(self, value: int) -> None:
        self._width_spin.setValue(value)

    def _pick_pen_color(self):
        color = QColorDialog.getColor(QColor(self._pen_color), self)
        if color.isValid():
            self._pen_color = color.name()
            self._update_btn_color(self._pen_btn, self._pen_color)
            self._emit()

    def _pick_fill_color(self):
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            self._fill_color = color.name()
            self._update_btn_color(self._fill_btn, self._fill_color)
            self._emit()

    def _update_btn_color(self, btn: QPushButton, color: str):
        btn.setStyleSheet(f"background-color: {color}; color: white;")

    def _emit(self):
        self.properties_changed.emit(self._pen_color, self.pen_width, self._fill_color)
```

**Step 5: 테스트 통과 확인**

```bash
pytest tests/test_toolbar.py -v
```

Expected: PASS (3/3)

**Step 6: Commit**

```bash
git add src/ui/toolbar.py src/ui/properties.py tests/test_toolbar.py
git commit -m "feat: 도구바 & 속성 패널"
```

---

## Task 8: 메인 윈도우 통합 (메뉴 액션 & 시그널 연결)

**Files:**
- Modify: `src/ui/main_window.py`
- Test: `tests/test_main_window_integration.py`

**Step 1: 테스트 작성**

```python
# tests/test_main_window_integration.py
import pytest
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow

@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])

def test_file_menu_has_open_action(app):
    window = MainWindow()
    actions = [a.text() for a in window.menuBar().actions()[0].menu().actions()]
    assert any("Open" in a for a in actions)

def test_file_menu_has_export_action(app):
    window = MainWindow()
    actions = [a.text() for a in window.menuBar().actions()[0].menu().actions()]
    assert any("Export" in a for a in actions)

def test_edit_menu_has_undo_redo(app):
    window = MainWindow()
    actions = [a.text() for a in window.menuBar().actions()[1].menu().actions()]
    assert any("Undo" in a for a in actions)
    assert any("Redo" in a for a in actions)
```

**Step 2: 테스트 실패 확인**

```bash
pytest tests/test_main_window_integration.py -v
```

Expected: FAIL

**Step 3: 메인 윈도우 통합 구현**

```python
# src/ui/main_window.py (전체 교체)
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QFileDialog, QStatusBar, QLabel
)
from PyQt6.QtGui import QKeySequence, QAction
from PyQt6.QtCore import Qt
from src.ui.canvas import Canvas
from src.ui.toolbar import Toolbar
from src.ui.properties import PropertiesPanel
from src.core.shape_manager import ShapeManager, ShapeType
from src.core.image_handler import ImageHandler
from src.utils.constants import (
    APP_NAME, OPEN_FILE_FILTER, SAVE_FILE_FILTER
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(900, 660)
        self._handler = ImageHandler()
        self._shape_manager = ShapeManager()
        self._canvas = Canvas(self._shape_manager)
        self._setup_menubar()
        self._setup_central()
        self._setup_statusbar()

    def _setup_menubar(self):
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

    def _setup_central(self):
        container = QWidget()
        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(0)

        # 도구바 + 속성 패널 행
        self._toolbar = Toolbar()
        self._props = PropertiesPanel()
        tool_row = QWidget()
        h_layout = QHBoxLayout(tool_row)
        h_layout.setContentsMargins(4, 2, 4, 2)
        h_layout.addWidget(self._toolbar)
        h_layout.addStretch()
        h_layout.addWidget(self._props)
        tool_row.setMaximumHeight(44)
        v_layout.addWidget(tool_row)

        # 캔버스 (스크롤 가능)
        scroll = QScrollArea()
        scroll.setWidget(self._canvas)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_layout.addWidget(scroll, stretch=1)

        self.setCentralWidget(container)

        # 시그널 연결
        self._toolbar.tool_changed.connect(self._on_tool_changed)
        self._props.properties_changed.connect(self._on_props_changed)

    def _setup_statusbar(self):
        self._status_label = QLabel("Ready")
        self.statusBar().addWidget(self._status_label)

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", OPEN_FILE_FILTER)
        if path:
            self._canvas.load_image(path)
            self._shape_manager.clear()
            self._status_label.setText(f"{path.split('/')[-1]}")

    def _export_file(self):
        if self._canvas.image is None:
            return
        path, selected_filter = QFileDialog.getSaveFileName(
            self, "Export Image", "", SAVE_FILE_FILTER
        )
        if path:
            fmt = selected_filter.split("(")[0].strip()
            self._handler.save(self._canvas.image, path, format=fmt or None)
            self._status_label.setText(f"Exported: {path.split('/')[-1]}")

    def _undo(self):
        self._shape_manager.undo()
        self._canvas.update()

    def _redo(self):
        self._shape_manager.redo()
        self._canvas.update()

    def _on_tool_changed(self, shape_type):
        if shape_type is not None:
            self._canvas.current_shape_type = shape_type

    def _on_props_changed(self, pen_color: str, pen_width: int, fill_color):
        self._canvas.pen_color = pen_color
        self._canvas.pen_width = pen_width
        self._canvas.fill_color = fill_color
```

**Step 4: 테스트 통과 확인**

```bash
pytest tests/test_main_window_integration.py -v
```

Expected: PASS (3/3)

**Step 5: Commit**

```bash
git add src/ui/main_window.py tests/test_main_window_integration.py
git commit -m "feat: 메인 윈도우 통합 (메뉴, 시그널 연결)"
```

---

## Task 9: 앱 진입점 & README (`main.py`, `README.md`)

**Files:**
- Create: `src/main.py`
- Create: `README.md`

**Step 1: 진입점 작성**

```python
# src/main.py
import sys
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.utils.constants import APP_NAME


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

**Step 2: README 작성**

```markdown
# simcut

간단한 사진 편집 데스크탑 앱 (Mac OS / Windows)

## 실행 방법

```bash
cd /Users/montecarlo/Downloads/2_AREA/apps/simcut
source .venv/bin/activate
python -m src.main
```

## 테스트

```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```
```

**Step 3: 실행 확인**

```bash
python -m src.main
```

Expected: simcut 창이 열림

**Step 4: Commit**

```bash
git add src/main.py README.md
git commit -m "feat: 앱 진입점 & README"
```

---

## Task 10: 전체 테스트 & 커버리지 확인

**Step 1: 전체 테스트 실행**

```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```

Expected: 모든 테스트 PASS, 커버리지 80%+

**Step 2: 실패한 테스트가 있다면**

각 실패 메시지를 확인하고 구현 수정 후 재실행.

**Step 3: Commit**

```bash
git add .
git commit -m "test: 전체 테스트 통과 확인"
```

---

## Task 11: Mac `.app` 패키징 (PyInstaller)

**Step 1: spec 파일 생성**

```bash
pyinstaller --name simcut --windowed --onefile src/main.py
```

**Step 2: 빌드**

```bash
pyinstaller simcut.spec
```

Expected: `dist/simcut.app` 생성

**Step 3: 실행 확인**

```bash
open dist/simcut.app
```

Expected: simcut 앱 정상 실행

**Step 4: Commit**

```bash
git add simcut.spec
git commit -m "chore: PyInstaller Mac 패키징 설정"
```

---

## 완료 체크리스트

- [ ] Task 1: 프로젝트 구조 & 가상환경
- [ ] Task 2: 상수 정의
- [ ] Task 3: 이미지 핸들러
- [ ] Task 4: 도형 데이터 모델 & Undo/Redo
- [ ] Task 5: 메인 윈도우 스켈레톤
- [ ] Task 6: 캔버스 위젯
- [ ] Task 7: 도구바 & 속성 패널
- [ ] Task 8: 메인 윈도우 통합
- [ ] Task 9: 앱 진입점 & README
- [ ] Task 10: 전체 테스트 & 커버리지 80%+
- [ ] Task 11: Mac `.app` 패키징
