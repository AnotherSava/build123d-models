import math

from .numbers import fmt

Point2D = tuple[float, float]


def emit_pencil_for(poly: list[Point2D], name: str) -> list[str]:
    lines = [f'{name} = Pencil(cross_section, start=({fmt(poly[0][0])}, {fmt(poly[0][1])}))']
    cur = poly[0]
    for nxt in poly[1:]:
        dx = nxt[0] - cur[0]
        dy = nxt[1] - cur[1]
        if abs(dy) < 1e-3 and dx > 0:
            lines.append(f'{name}.right({fmt(dx)})')
        elif abs(dy) < 1e-3 and dx < 0:
            lines.append(f'{name}.left({fmt(-dx)})')
        elif abs(dx) < 1e-3 and dy > 0:
            lines.append(f'{name}.up({fmt(dy)})')
        elif abs(dx) < 1e-3 and dy < 0:
            lines.append(f'{name}.down({fmt(-dy)})')
        else:
            length = math.hypot(dx, dy)
            angle = math.degrees(math.atan2(dy, dx))
            lines.append(f'{name}.draw({fmt(length)}, {fmt(angle, 2)})')
        cur = nxt
    return lines
