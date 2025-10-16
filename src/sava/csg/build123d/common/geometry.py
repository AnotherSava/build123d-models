from enum import IntEnum
from math import cos, sin, radians

from build123d import Vector


# Ways to align one 2d vector (or another else) to another
class Alignment(IntEnum):
    LL = 1 # left side, attach to the left
    LR = 2 # left side, attach to the right
    C = 3 # align both centres
    RL = 4 # right side, attach to the left
    RR = 5 # right side, attach to the right


class Side(IntEnum):
    S = 180
    E = 270
    N = 0
    W = 90

    @property
    def horizontal(self) -> bool:
        return self in (Side.E, Side.W)

    @property
    def vertical(self) -> bool:
        return self in (Side.S, Side.N)


# angle is measured in degrees CCW from axis Y
def createVector(length: float, angle: float) -> Vector:
    return Vector(-length * sin(radians(angle)), length * cos(radians(angle)))

# args = series of lengths and angles, where angles are measured in degrees CCW from axis Y
def shiftVector(vector: Vector, *args: float) -> Vector:
    assert len(args) >= 2 and len(args) % 2 == 0
    result = vector
    for i in range(0, len(args), 2):
        result += createVector(args[i], args[i + 1])

    return result
