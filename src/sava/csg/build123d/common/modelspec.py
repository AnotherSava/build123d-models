from dataclasses import dataclass
from pathlib import Path

from sava.csg.build123d.common.exporter import clear, export, export_stl, save_3mf
from sava.csg.build123d.common.smartsolid import SmartSolid


@dataclass
class ModelSpec:
    """Declarative description of an exportable model.

    Decouples *building* a model from *where* its files land, so a single build
    can feed both the CLI export (to the committed location) and the regression
    test suite (to a temp dir). `scene` holds the assembled, coloured parts for
    the 3MF visualization; `prints` holds the print-layout parts written as
    per-part STLs. Leave `prints` unset when the model prints in its scene pose.
    """

    name: str
    output_dir: str
    scene: list[SmartSolid]
    prints: list[SmartSolid] | None = None

    @property
    def print_parts(self) -> list[SmartSolid]:
        return self.scene if self.prints is None else self.prints


def export_model(spec: ModelSpec, output_root: str | None = None, update_current: bool | None = None) -> None:
    """Export a ModelSpec: assembled 3MF scene first, then per-part STLs.

    Writes under `spec.output_dir` (the committed location) by default. Pass
    `output_root` to redirect under `<output_root>/<name>` — the regression
    suite uses this to export into a temp dir without touching committed files.
    `update_current` copies the 3MF to the current-model file for the F3D
    viewer; it defaults to True only for the real location, so tests never
    clobber it.
    """
    base = Path(spec.output_dir) if output_root is None else Path(output_root) / spec.name
    if update_current is None:
        update_current = output_root is None

    clear()
    export(*spec.scene)
    save_3mf(str(base / "export.3mf"), current=update_current)
    export_stl(str(base / "stl"), *spec.print_parts, clean=True)
