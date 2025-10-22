from enum import IntEnum, auto
from math import cos, sin, radians, atan2, degrees

from build123d import Vector, Axis


# Ways to align one 2d vector (or another else) to another
class Alignment(IntEnum):
    LL = auto() # left side, attach to the left
    L = auto() # left side, attach to the centre
    LR = auto() # left side, attach to the right
    C = auto() # align both centres
    RL = auto() # right side, attach to the left
    R = auto() # right side, attach to the centre
    RR = auto() # right side, attach to the right

    def shift_towards_centre(self, value: float) -> float:
        assert self != Alignment.C

        return value if self in (Alignment.LL, Alignment.LR) else -value


class Direction(IntEnum):
    S = 180
    E = 270
    N = 0
    W = 90

    @property
    def horizontal(self) -> bool:
        return self in (Direction.E, Direction.W)

    @property
    def vertical(self) -> bool:
        return self in (Direction.S, Direction.N)

    @property
    def axis(self) -> Axis:
        return Axis.X if self.horizontal else Axis.Y

    @property
    def orthogonal_axis(self) -> Axis:
        return Axis.Y if self.horizontal else Axis.X

    @property
    def alignment_further(self) -> Alignment:
        return Alignment.RR if self in [Direction.N, Direction.E] else Alignment.LL

    @property
    def alignment_middle(self) -> Alignment:
        return Alignment.R if self in [Direction.N, Direction.E] else Alignment.L

    @property
    def alignment_closer(self) -> Alignment:
        return Alignment.RL if self in [Direction.N, Direction.E] else Alignment.LR

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

def get_angle(vector: Vector):
    return -degrees(atan2(vector.X, vector.Y))
