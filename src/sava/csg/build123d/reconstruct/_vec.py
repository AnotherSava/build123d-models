import math

Vec = tuple[float, float, float]


def vsub(a: Vec, b: Vec) -> Vec:
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])


def vadd(a: Vec, b: Vec) -> Vec:
    return (a[0]+b[0], a[1]+b[1], a[2]+b[2])


def vmul(a: Vec, k: float) -> Vec:
    return (a[0]*k, a[1]*k, a[2]*k)


def vdot(a: Vec, b: Vec) -> float:
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]


def vcross(a: Vec, b: Vec) -> Vec:
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def vlen(a: Vec) -> float:
    return math.sqrt(vdot(a, a))


def vnorm(a: Vec) -> Vec:
    n = vlen(a)
    return (a[0]/n, a[1]/n, a[2]/n) if n > 1e-12 else a
