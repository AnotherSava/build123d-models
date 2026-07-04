"""Geometry signatures for model regression testing.

Mesh bytes are not a viable regression baseline: 3MF is a zip (non-deterministic
timestamps/UUIDs) and STL tessellation density drifts with the CAD-kernel
version even when the geometry is unchanged. Instead we compare a small set of
B-rep invariants computed directly on the built solids — volume, surface area,
bounding-box size, mass centre, and solid/face/edge/vertex counts. These are
sensitive to real geometry changes from evolving common code, yet robust to
tessellation/library noise. The signatures are committed per model as
`signature.json` alongside the exported meshes.
"""

import json
from math import isclose
from pathlib import Path
from typing import Any

from build123d import CenterOf, ShapeList

from sava.csg.build123d.common.exporter import get_path
from sava.csg.build123d.common.modelspec import ModelSpec
from sava.csg.build123d.common.smartsolid import get_solid


def _leaf_shapes(part: Any) -> list[Any]:
    solid = get_solid(part)
    if isinstance(solid, (list, tuple, ShapeList)):
        return list(solid)
    return [solid]


def _shape_volume(shape: Any) -> float:
    # build123d's Compound.volume mis-reports 0 for a mirrored multi-solid compound;
    # summing per-solid volumes is correct and identical for single solids / valid compounds.
    solids = shape.solids()
    return sum(s.volume for s in solids) if solids else shape.volume


def _aggregate(shapes: list[Any]) -> dict[str, Any]:
    volume = sum(_shape_volume(s) for s in shapes)
    bbox = shapes[0].bounding_box()
    for s in shapes[1:]:
        bbox = bbox.add(s.bounding_box())
    com = [0.0, 0.0, 0.0]
    for s in shapes:
        sv = _shape_volume(s)
        c = s.center(CenterOf.MASS)
        com[0] += c.X * sv
        com[1] += c.Y * sv
        com[2] += c.Z * sv
    com = [c / volume for c in com] if volume else [0.0, 0.0, 0.0]
    return {
        "volume": round(volume, 4),
        "area": round(sum(s.area for s in shapes), 4),
        "bbox": [round(bbox.size.X, 5), round(bbox.size.Y, 5), round(bbox.size.Z, 5)],
        "com": [round(c, 5) for c in com],
        "solids": sum(len(s.solids()) for s in shapes),
        "faces": sum(len(s.faces()) for s in shapes),
        "edges": sum(len(s.edges()) for s in shapes),
        "vertices": sum(len(s.vertices()) for s in shapes),
    }


def signature(spec: ModelSpec) -> dict[str, dict[str, Any]]:
    """Compute the geometry signature of a model, keyed by STL label.

    Parts are grouped by label to mirror `save_stl`'s one-file-per-label output,
    so each signature entry corresponds to a committed STL.
    """
    groups: dict[str, list[Any]] = {}
    for part in spec.print_parts:
        label = getattr(part, "label", None) or spec.name
        groups.setdefault(label, []).extend(_leaf_shapes(part))
    return {label: _aggregate(shapes) for label, shapes in groups.items()}


_FLOAT_FIELDS = ("volume", "area")
_VECTOR_FIELDS = ("bbox", "com")
_COUNT_FIELDS = ("solids", "faces", "edges", "vertices")


def compare(current: dict[str, dict[str, Any]], reference: dict[str, dict[str, Any]], rtol: float = 1e-4, atol: float = 1e-4) -> list[str]:
    """Return a list of human-readable drift descriptions; empty means a match.

    Float and vector fields compare within tolerance (robust to kernel float
    noise); counts must match exactly (a topology change is a real change — if a
    kernel upgrade shifts a count without altering geometry, re-baseline).
    """
    diffs = []
    if set(current) != set(reference):
        diffs.append(f"labels differ: {sorted(current)} vs reference {sorted(reference)}")
    for label in sorted(set(current) & set(reference)):
        cur, ref = current[label], reference[label]
        for field in _FLOAT_FIELDS:
            if not isclose(cur[field], ref[field], rel_tol=rtol, abs_tol=atol):
                diffs.append(f"{label}.{field}: {cur[field]} != reference {ref[field]}")
        for field in _VECTOR_FIELDS:
            for i, (c, r) in enumerate(zip(cur[field], ref[field], strict=True)):
                if not isclose(c, r, rel_tol=rtol, abs_tol=atol):
                    diffs.append(f"{label}.{field}[{i}]: {c} != reference {r}")
        for field in _COUNT_FIELDS:
            if cur[field] != ref[field]:
                diffs.append(f"{label}.{field}: {cur[field]} != reference {ref[field]}")
    return diffs


def reference_path(spec: ModelSpec) -> Path:
    return Path(get_path(spec.output_dir, "signature.json"))


def load_reference(spec: ModelSpec) -> dict[str, dict[str, Any]]:
    path = reference_path(spec)
    if not path.exists():
        raise FileNotFoundError(f"No signature baseline for '{spec.name}' at {path}. Create it with MODEL_REGRESSION_REBASELINE=1 pytest ...")
    return json.loads(path.read_text())


def save_reference(spec: ModelSpec, sig: dict[str, dict[str, Any]]) -> None:
    path = reference_path(spec)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sig, indent=2, sort_keys=True) + "\n")
