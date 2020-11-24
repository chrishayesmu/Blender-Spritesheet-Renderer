import collections
from mathutils import Vector

class Bounds:

    def __init__(self):
        self.center = None
        self.maxPoint = None
        self.minPoint = None
        self.size = None

    def __str__(self):
        return "Bounds: center = {}, min = {}, max = {}, size = {}".format(self.center, self.minPoint, self.maxPoint, self.size)

    def encapsulate(self, other):
        """Expands this Bounds object to fully include the bounds described by other"""

        valuesByAxis = list(zip(self.minPoint, self.maxPoint, other.minPoint, other.maxPoint))
        maxPoint = [max(vals) for vals in valuesByAxis]
        minPoint = [min(vals) for vals in valuesByAxis]

        newBounds = Bounds.fromMinAndMaxPoints(minPoint, maxPoint)
        self.center = newBounds.center
        self.maxPoint = newBounds.maxPoint
        self.minPoint = newBounds.minPoint
        self.size = newBounds.size

        return self # for chaining

    @staticmethod
    def forObject(obj):
        """Creates a Bounds object based on the bounding box of the given Blender object"""
        # Adopted from https://blender.stackexchange.com/a/32288/104252
        localCorners = obj.bound_box[:]
        coords = [obj.matrix_world @ Vector(c[:]) for c in localCorners]

        # Group values by which axis they belong to
        # Ex: if coords = [(1, 2, 3), (4, 5, 6), (7, 8, 9)]
        # then   coordsByAxis = [(1, 4, 7), (2, 5, 8), (3, 6, 9)]
        coordsByAxis = zip(*coords)

        axisInfo = collections.namedtuple('axis_bounds_info', 'max min distance')
        data = {}

        # For each axis, find the min/max values and the distance between them
        for (axis, _list) in zip('xyz', coordsByAxis):
            axisMax = max(_list)
            axisMin = min(_list)
            info = axisInfo(
                axisMax,
                axisMin,
                axisMax - axisMin
            )

            data[axis] = info

        maxPoint = (data["x"].max, data["y"].max, data["z"].max)
        minPoint = (data["x"].min, data["y"].min, data["z"].min)
        
        return Bounds.fromMinAndMaxPoints(minPoint, maxPoint)

    @staticmethod
    def fromCenterAndSize(center, size):
        bounds = Bounds()
        bounds.center = center
        bounds.maxPoint = [c + s / 2 for (c, s) in zip(center, size)]
        bounds.minPoint = [c - s / 2 for (c, s) in zip(center, size)]
        bounds.size = size

        return bounds

    @staticmethod
    def fromMinAndMaxPoints(minPoint, maxPoint):
        center = Bounds._midpoint(minPoint, maxPoint)
        size = Bounds._distanceByAxis(minPoint, maxPoint)

        bounds = Bounds()
        bounds.center = center
        bounds.maxPoint = maxPoint
        bounds.minPoint = minPoint
        bounds.size = size

        return bounds

    @staticmethod
    def _distanceByAxis(point1, point2):
        xDist = abs(point1[0] - point2[0])
        yDist = abs(point1[1] - point2[1])
        zDist = abs(point1[2] - point2[2])

        return (xDist, yDist, zDist)

    @staticmethod
    def _midpoint(point1, point2):
        x = (point1[0] + point2[0]) / 2
        y = (point1[1] + point2[1]) / 2
        z = (point1[2] + point2[2]) / 2

        return (x, y, z)