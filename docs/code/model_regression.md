# Model regression suite

Guards committed models against **silent geometry changes** when common code
(SmartSolid, SmartBox, Pencil, the exporter, …) evolves.

```bash
venv/Scripts/python.exe -m pytest tests/ -m regression
```

The suite is slow and grows with every model, so it is **excluded from the
default `pytest tests/` run** via the `regression` marker (`pytest.ini`) — the
frequent base suite stays fast. It runs deliberately, in two places:

- **`/commit`** — the commit skill runs `.claude/commit-checks.sh` (base suite,
  then the regression suite) before planning commits, and blocks on failure.
- **Development** — the project `CLAUDE.md` instructs Claude to run it
  (`pytest tests/ -m regression`) after substantive changes under `common/`.

## Why signatures, not mesh bytes

The obvious approach — regenerate each model and byte-compare against the
committed `.3mf` / `.stl` — does not work:

- **3MF is never byte-reproducible.** It is a zip; lib3MF embeds timestamps and
  UUIDs, so every write differs.
- **STL tessellation drifts with the CAD kernel.** The same solid meshes to a
  different triangle count across build123d/OCP versions (observed:
  42 622 → 43 054 triangles for `marker_holder`, identical geometry). Byte-locking
  the meshes would make the suite fail on every dependency bump.

Instead we compare a compact set of **B-rep invariants** computed on the built
solids — volume, surface area, bounding-box size, mass centre, and
solid/face/edge/vertex counts — with relative tolerance. These are sensitive to
real geometry changes (a 0.1 mm wall-thickness change is caught) yet immune to
tessellation noise. Each model's baseline is committed as `signature.json`
beside its meshes.

The test also runs the **real** `export_model` pipeline into a temp dir, so a
regression that breaks 3MF/STL writing (not just geometry) is caught too.

## How a model plugs in

Both the CLI export and the test drive the same `build()` → `ModelSpec` →
`export_model` path (`common/modelspec.py`), so there is one export mechanism,
not two:

```python
def build() -> ModelSpec:
    model = MarkerHolder(MarkerHolderDimensions()).create()
    return ModelSpec(name="marker_holder", output_dir="models/other/marker_holder", scene=[model])

if __name__ == "__main__":
    export_model(build())
```

`ModelSpec.scene` are the assembled, coloured parts for the 3MF; set `prints`
separately when the print layout differs from the scene pose (see the
arrange-scene pattern in `tray.py` / `splitter.py`). Signatures are keyed by
part **label**, mirroring the one-STL-per-label output.

## Adding a model

1. Give the model module a `build() -> ModelSpec` and route its `__main__`
   through `export_model(build())` (drop the hand-wired `export_3mf`/`export_stl`
   calls). Models that export at *import time* (e.g. `grand_austria_hotel/*`) must
   first move that work into `build()` / `__main__`.
2. Register it in `MODEL_BUILDERS` in `test_model_regression.py`.
3. Create the baseline once and commit it with the model:
   ```bash
   MODEL_REGRESSION_REBASELINE=1 venv/Scripts/python.exe -m pytest tests/ -m regression
   ```

## Blessing an intentional change

When you deliberately change a model's geometry, regenerate its baseline with
the same `MODEL_REGRESSION_REBASELINE=1` run and commit the updated
`signature.json` alongside the model change. A count mismatch caused purely by a
CAD-kernel upgrade (geometry unchanged) is re-baselined the same way.
