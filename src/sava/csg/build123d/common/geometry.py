from enum import IntEnum, auto
from math import cos, sin, radians

from build123d import Vector


# Ways to align one 2d vector (or another else) to another
class Alignment(IntEnum):
    LL = auto() # left side, attach to the left
    L = auto() # left side, attach to the centre
    LR = auto() # left side, attach to the right
    C = auto() # align both centres
    RL = auto() # right side, attach to the left
    R = auto() # right side, attach to the centre
    RR = auto() # right side, attach to the right


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
def create_vector(length: float, angle: float) -> Vector:
    return Vector(-length * sin(radians(angle)), length * cos(radians(angle)))

# args = series of lengths and angles, where angles are measured in degrees CCW from axis Y
def shift_vector(vector: Vector, *args: float) -> Vector:
    assert len(args) >= 2 and len(args) % 2 == 0
    result = vector
    for i in range(0, len(args), 2):
        result += create_vector(args[i], args[i + 1])

    return result
