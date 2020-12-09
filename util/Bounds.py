from __future__ import annotations

import bpy
import collections
from mathutils import Vector
from typing import Tuple

class Bounds:

    def __init__(self):
        self.center = None
        self.max_point = None
        self.min_point = None
        self.size = None

    def __str__(self):
        return "Bounds: center = {}, min = {}, max = {}, size = {}".format(self.center, self.min_point, self.max_point, self.size)

    def encapsulate(self, other: Bounds) -> Bounds:
        """Expands this Bounds object to fully include the bounds described by other"""

        values_by_axis = list(zip(self.min_point, self.max_point, other.min_point, other.max_point))
        max_point = [max(vals) for vals in values_by_axis]
        min_point = [min(vals) for vals in values_by_axis]

        new_bounds = Bounds.from_min_and_max_points(min_point, max_point)
        self.center = new_bounds.center
        self.max_point = new_bounds.max_point
        self.min_point = new_bounds.min_point
        self.size = new_bounds.size

        return self # for chaining

    @staticmethod
    def for_object(obj: bpy.types.Object) -> Bounds:
        """Creates a Bounds object based on the bounding box of the given Blender object"""
        # Adopted from https://blender.stackexchange.com/a/32288/104252
        local_corners = obj.bound_box[:]
        coords = [obj.matrix_world @ Vector(c[:]) for c in local_corners]

        # Group values by which axis they belong to
        # Ex: if coords = [(1, 2, 3), (4, 5, 6), (7, 8, 9)]
        # then   coordsByAxis = [(1, 4, 7), (2, 5, 8), (3, 6, 9)]
        coords_by_axis = zip(*coords)

        axis_info = collections.namedtuple('axis_bounds_info', 'max min distance')
        data = {}

        # For each axis, find the min/max values and the distance between them
        for (axis, _list) in zip('xyz', coords_by_axis):
            axis_max = max(_list)
            axis_min = min(_list)
            info = axis_info(
                axis_max,
                axis_min,
                axis_max - axis_min
            )

            data[axis] = info

        max_point = (data["x"].max, data["y"].max, data["z"].max)
        min_point = (data["x"].min, data["y"].min, data["z"].min)

        return Bounds.from_min_and_max_points(min_point, max_point)

    @staticmethod
    def from_center_and_size(center: Tuple[float, float, float], size: Tuple[float, float, float]) -> Bounds:
        bounds = Bounds()
        bounds.center = center
        bounds.max_point = [c + s / 2 for (c, s) in zip(center, size)]
        bounds.min_point = [c - s / 2 for (c, s) in zip(center, size)]
        bounds.size = size

        return bounds

    @staticmethod
    def from_min_and_max_points(min_point: Tuple[float, float, float], max_point: Tuple[float, float, float]) -> Bounds:
        center = Bounds._midpoint(min_point, max_point)
        size = Bounds._distance_by_axis(min_point, max_point)

        bounds = Bounds()
        bounds.center = center
        bounds.max_point = max_point
        bounds.min_point = min_point
        bounds.size = size

        return bounds

    @staticmethod
    def _distance_by_axis(point1: Tuple[float, float, float], point2: Tuple[float, float, float]) -> Tuple[float, float, float]:
        x_dist = abs(point1[0] - point2[0])
        y_dist = abs(point1[1] - point2[1])
        z_dist = abs(point1[2] - point2[2])

        return (x_dist, y_dist, z_dist)

    @staticmethod
    def _midpoint(point1: Tuple[float, float, float], point2: Tuple[float, float, float]) -> Tuple[float, float, float]:
        x = (point1[0] + point2[0]) / 2
        y = (point1[1] + point2[1]) / 2
        z = (point1[2] + point2[2]) / 2

        return (x, y, z)