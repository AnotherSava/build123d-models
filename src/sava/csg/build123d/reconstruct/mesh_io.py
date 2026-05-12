import os
import struct

from ._vec import Vec

Face = tuple[int, int, int]


def read_off(path: str) -> tuple[list[Vec], list[Face]]:
    with open(path) as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    assert lines[0].upper().startswith('OFF')
    nv, nf, _ = map(int, lines[1].split())
    verts: list[Vec] = [tuple(map(float, lines[2 + i].split())) for i in range(nv)]
    faces: list[Face] = []
    for i in range(nf):
        parts = list(map(int, lines[2 + nv + i].split()))
        n = parts[0]
        assert n == 3, f'non-triangle face: {parts}'
        faces.append(tuple(parts[1:4]))
    return verts, faces


def read_stl(path: str) -> tuple[list[Vec], list[Face]]:
    with open(path, 'rb') as f:
        header = f.read(80)
        rest = f.read()
    is_ascii = header[:5] == b'solid' and b'facet' in rest[:1024]
    if is_ascii:
        return _read_stl_ascii(path)
    return _read_stl_binary(path)


def _read_stl_binary(path: str) -> tuple[list[Vec], list[Face]]:
    with open(path, 'rb') as f:
        f.read(80)
        (n_tri,) = struct.unpack('<I', f.read(4))
        verts_by_key: dict[tuple[float, float, float], int] = {}
        verts: list[Vec] = []
        faces: list[Face] = []
        for _ in range(n_tri):
            f.read(12)  # normal
            tri: list[int] = []
            for _v in range(3):
                x, y, z = struct.unpack('<fff', f.read(12))
                key = (x, y, z)
                idx = verts_by_key.get(key)
                if idx is None:
                    idx = len(verts)
                    verts_by_key[key] = idx
                    verts.append((x, y, z))
                tri.append(idx)
            f.read(2)  # attribute byte count
            faces.append((tri[0], tri[1], tri[2]))
    return verts, faces


def _read_stl_ascii(path: str) -> tuple[list[Vec], list[Face]]:
    verts_by_key: dict[tuple[float, float, float], int] = {}
    verts: list[Vec] = []
    faces: list[Face] = []
    with open(path) as f:
        tri: list[int] = []
        for line in f:
            line = line.strip()
            if line.startswith('vertex'):
                _, sx, sy, sz = line.split()
                key = (float(sx), float(sy), float(sz))
                idx = verts_by_key.get(key)
                if idx is None:
                    idx = len(verts)
                    verts_by_key[key] = idx
                    verts.append(key)
                tri.append(idx)
                if len(tri) == 3:
                    faces.append((tri[0], tri[1], tri[2]))
                    tri = []
    return verts, faces


def read_mesh(path: str) -> tuple[list[Vec], list[Face]]:
    ext = os.path.splitext(path)[1].lower()
    if ext == '.off':
        return read_off(path)
    if ext == '.stl':
        return read_stl(path)
    raise ValueError(f'Unsupported mesh format: {ext}')
