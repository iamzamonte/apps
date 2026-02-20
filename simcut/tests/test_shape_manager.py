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


def test_undo_on_empty_does_nothing():
    manager = ShapeManager()
    manager.undo()
    assert len(manager.shapes) == 0


def test_redo_on_empty_does_nothing():
    manager = ShapeManager()
    manager.redo()
    assert len(manager.shapes) == 0


def test_replace_updates_shape():
    manager = ShapeManager()
    original = Shape(ShapeType.RECTANGLE, 0, 0, 50, 50, "#000", 1, None)
    manager.add(original)
    moved = Shape(ShapeType.RECTANGLE, 100, 100, 50, 50, "#000", 1, None)
    manager.replace(0, moved)
    assert manager.shapes[0].x == 100
    assert manager.shapes[0].y == 100


def test_replace_out_of_range_raises():
    manager = ShapeManager()
    shape = Shape(ShapeType.RECTANGLE, 0, 0, 50, 50, "#000", 1, None)
    with pytest.raises(IndexError):
        manager.replace(0, shape)


def test_new_add_clears_redo_stack():
    manager = ShapeManager()
    shape = Shape(ShapeType.RECTANGLE, 0, 0, 50, 50, "#000", 1, None)
    manager.add(shape)
    manager.undo()
    manager.add(shape)
    manager.redo()  # redo stack이 비어있으므로 변화 없음
    assert len(manager.shapes) == 1
