from __future__ import annotations

from mathutils import Vector
from typing import Iterable, Optional, Tuple

class Bounds2D:

    def __init__(self):
        self.min_point: Vector = None
        self.max_point: Vector = None

    @property
    def center(self) -> Optional[Vector[float, float]]:
        return 0.5 * (self.min_point + self.max_point) if self.min_point is not None and self.max_point is not None else None

    @property
    def center_3d(self) -> Optional[Vector[float, float, float]]:
        c = self.center
        return Vector( ( c[0], c[1], 0 ) ) if c is not None else None

    @property
    def size(self) -> Optional[Vector[float, float]]:
        return (self.max_point - self.min_point) if self.min_point is not None and self.max_point is not None else None

    def encapsulate(self, bounds: Bounds2D) -> Bounds2D:
        self.min_point = Vector((
            min(self.min_point[0], bounds.min_point[0]),
            min(self.min_point[1], bounds.min_point[1])
        ))

        self.max_point = Vector((
            max(self.max_point[0], bounds.max_point[0]),
            max(self.max_point[1], bounds.max_point[1])
        ))

        return self

    @staticmethod
    def from_points(points: Iterable[Tuple[float, float]]) -> Bounds2D:
        min_point = (
            min([p[0] for p in points]),
            min([p[1] for p in points])
        )

        max_point = (
            max([p[0] for p in points]),
            max([p[1] for p in points])
        )

        return Bounds2D.from_min_and_max_points(min_point, max_point)

    @staticmethod
    def from_min_and_max_points(min_point: Tuple[float, float], max_point: Tuple[float, float]) -> Bounds2D:
        bounds = Bounds2D()
        bounds.min_point = min_point
        bounds.max_point = max_point
        return bounds