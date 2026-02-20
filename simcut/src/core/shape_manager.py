from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class ShapeType(Enum):
    RECTANGLE = "rectangle"
    ELLIPSE = "ellipse"


@dataclass(frozen=True)
class Shape:
    shape_type: ShapeType
    x: int
    y: int
    width: int
    height: int
    pen_color: str
    pen_width: int
    fill_color: Optional[str]


class ShapeManager:
    def __init__(self) -> None:
        self._shapes: List[Shape] = []
        self._undo_stack: List[Shape] = []

    @property
    def shapes(self) -> List[Shape]:
        return list(self._shapes)

    def add(self, shape: Shape) -> None:
        self._shapes = [*self._shapes, shape]
        self._undo_stack = []

    def undo(self) -> None:
        if not self._shapes:
            return
        removed = self._shapes[-1]
        self._shapes = self._shapes[:-1]
        self._undo_stack = [*self._undo_stack, removed]

    def redo(self) -> None:
        if not self._undo_stack:
            return
        restored = self._undo_stack[-1]
        self._undo_stack = self._undo_stack[:-1]
        self._shapes = [*self._shapes, restored]

    def replace(self, index: int, shape: Shape) -> None:
        """지정 인덱스의 도형을 새 도형으로 교체합니다 (불변 방식)."""
        if not (0 <= index < len(self._shapes)):
            raise IndexError(f"Shape index {index} out of range")
        self._shapes = [*self._shapes[:index], shape, *self._shapes[index + 1:]]

    def remove(self, index: int) -> None:
        """지정 인덱스의 도형을 삭제합니다 (불변 방식)."""
        if not (0 <= index < len(self._shapes)):
            raise IndexError(f"Shape index {index} out of range")
        self._shapes = [*self._shapes[:index], *self._shapes[index + 1:]]
        self._undo_stack = []

    def clear(self) -> None:
        self._shapes = []
        self._undo_stack = []
