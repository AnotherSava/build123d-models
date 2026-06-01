---
name: model-reconstruct
description: Reconstruct a 2.5D mesh (STL/OFF) into parametric build123d code and integrate it into a model
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

The `sava.csg.build123d.reconstruct` module converts 2.5D-extrudable mesh files into build123d code. This skill captures the end-to-end interactive workflow: run the algorithm, integrate its output into a model class, parametrize the magic numbers, and clean up tessellation artefacts. Algorithmic depth lives in `docs/code/reconstruct/`; consult it only when iterating on the algorithm itself or debugging a surprising reconstruction.

## Context

- Most recent input meshes: !`ls -t input/*/*.stl input/*/*.off 2>/dev/null | head -3`
- Most recent model files: !`ls -t src/sava/csg/build123d/models/*/*.py 2>/dev/null | head -5`

1. **Identify input mesh and target model.**
   - **Input mesh**: take the top entry from **Most recent input meshes** (Context above) as the candidate. Confirm the path with the user before proceeding.
   - **Target model**: scan **Most recent model files** for a name that aligns with the mesh's subfolder (e.g. `input/cable-channel/...` ↔ `cablechannel.py`).
     - **If aligned**: confirm both mesh and model with the user in a single question.
     - **If not aligned**: confirm only the mesh; then ask the user for the target model. If no suitable model exists, run the `model-create` skill first to scaffold it, then return here.

2. **Run the reconstruction CLI**:
   ```bash
   venv/Scripts/python.exe -m sava.csg.build123d.reconstruct input/<feature>/<part>.stl --out tmp/reconstructed_<part>.py
   ```
   - If the CLI exits non-zero, the mesh is not 2.5D-extrudable. Read the error message (it names the offending plane count / orientation) and report the limitation to the user. Common causes: lofts, free-form surfaces, cylinders perpendicular to the extrusion axis. Stop the skill — no reconstruction is possible without changing the input.
   - On success, read `tmp/reconstructed_<part>.py`.
   - **Precision tuning**: the default threshold (`--sig-area-frac 0.005` = 0.5% of total mesh area) drops planes that are mostly tessellation noise. If the user later spots small features missing in the analysis (tiny cavities, small fillets, mounting bosses), re-run with a lower threshold — `--sig-area-frac 1e-5` includes anything down to 0.001%. The cable-channel STL needs `1e-5` to pick up its 0.75 mm² triangular cavity back walls.

3. **Inspect the emitted code.** Expect:
   - A comment header naming the extrusion axis, datum plane, and frame vectors.
   - One `Pencil` per polygon loop, plus `SmarterCone.cylinder(...)` / `SmartBox(...)` for detected circles / rectangles.
   - `body = <Pencil or SmarterCone>` → `blade = body.extrude(...)` for the main body silhouette.
   - One `fuse` / `cut` block per non-body layer named `back_protrusion`, `pocket`, or `front_protrusion`.
   - A trailing `cross_section = Plane(...)` block that maps the local result back to the source-mesh world frame.

4. **Analyze the object before integrating.** Present a short description to the user covering:
   - **What the part is** in plain terms (geometric shape, its purpose if obvious from the silhouette — "U-channel with chamfered top edges and a snap-lock notch", "petal-shaped blade with a pivot pin", etc.). Walk through the emitted Pencil strokes mentally to reconstruct the cross-section profile.
   - **How it will be represented in the framework**. The part doesn't have to be a single Pencil.extrude — the emit will naturally fall into one of these shapes. Pick the one that best fits the geometry and explain it:
     - **Single uniform extrusion**: one `Pencil` traces the cross-section, `.extrude(L)` builds the body. Use when the emit has only `front` + `back` cap layers (no protrusion / pocket layers).
     - **Body + auxiliary pieces**: one dominant `Pencil.extrude` with additional `.fuse()` / `.cut()` of smaller extruded pieces (or `SmarterCone.cylinder` / `SmartBox` primitives). The emit's `back_protrusion` / `front_protrusion` / `pocket` layers map directly onto this — most multi-layer parts work this way.
     - **Multi-section extrusion**: when the cross-section changes substantially mid-length and the "body + auxiliary" framing would be awkward, split the part along the extrusion axis into uniform-profile chunks and reconstruct each separately (typically by cropping the source mesh and re-running the CLI on each piece). Stitch the chunks in the model's `create()` via `.align()` + `.fuse()`. Use sparingly — the layered emit handles most cases cleanly.
   - Identify the orientation in local `Plane.XY` (which axis is the extrusion direction, where the cross-section lives).
   Confirm this description with the user before writing code. Adjust based on their input — they may rename the part, prefer a different representation strategy, or want simplifications applied early (step 8).

5. **Integrate into the model class with literal values.** Replace the target `create_<part>` method body with the emitted geometry, keeping every emit literal as-is (no parametrization yet — that comes after the geometry is confirmed correct). Two consistent conventions:
   - **Build in default `Plane.XY`** in local coords. Drop the trailing `cross_section = Plane(...)` block — the model places the part via its own `.align()` / `.move()` at the call site.
   - **`blade` is the algorithm's variable name** for the assembled SmartSolid. Rename it to whatever fits the model (e.g. `blade`, `plate`, `cover`, `channel`).
   - **If the model was just scaffolded by `model-create`**, remove the placeholder `length` / `width` / `height` fields from the `<Name>Dimensions` dataclass — they came from the scaffold and have no role in the reconstructed geometry. Leave the dataclass empty for now; fields get added in step 6.
   - See `src/sava/csg/build123d/models/other/dispenserbottlemount.py::create_blade` for the reference integration pattern.

6. **Confirm the integrated model with the user.** Run the model's `__main__` and confirm the export builds without OCCT warnings. Present the result to the user (path to `models/<group>/<name>/export.3mf`, bbox / volume if useful) and wait for confirmation that the geometry is correct before proceeding. Mismatches surface here are easier to fix while the code still mirrors the emit one-to-one — parametrization, simplification, and cleanup come next and obscure the diff against the emit.

7. **Detect walls — parallel-surface pairs with material between them.** Before parametrizing, enumerate wall thicknesses in the part. Walls show up as pairs of parallel planes (sign-canonicalized normals match) with the offset difference = wall thickness. Use this snippet on the source mesh:
   ```python
   from sava.csg.build123d.reconstruct.mesh_io import read_mesh
   from sava.csg.build123d.reconstruct.planes import cluster_planes
   from collections import defaultdict
   verts, faces = read_mesh('input/<feature>/<part>.stl')
   planes = cluster_planes(verts, faces)
   groups = defaultdict(list)
   for p in planes:
       groups[tuple(round(c, 3) for c in p.normal)].append(p)
   for n, group in groups.items():
       if len(group) < 2: continue
       group.sort(key=lambda p: p.d)
       for a, b in zip(group, group[1:]):
           print(f'n={n}  d1={a.d:.3f} d2={b.d:.3f}  thickness={b.d - a.d:.3f}')
   ```
   - Wall thicknesses that **repeat** across multiple pairs (e.g., floor thickness == outer-wall thickness == rim thickness == 1.5 mm) are the strongest parametrization candidates — lift them to a single `wall_thickness` (or similar) field that every site references.
   - Single-occurrence thicknesses may still be parametrization candidates if they have a semantic role (channel cavity width, pin radius, slot depth), but they don't get the same compounding benefit as a repeating thickness.
   - Present detected thicknesses to the user, calling out which ones repeat. Confirm the wall-thickness field name and any other dims to lift before writing code.

8. **Parametrize the magic numbers.** Now that the geometry is confirmed correct and walls are identified, lift literals that describe *tunable dimensions* into the model's `<Name>Dimensions` dataclass and reference `dim.<field>` instead. Propose candidates to the user one cluster at a time (the wall thicknesses from step 7, overall length, notch depth, etc.) and let them confirm which to lift. Typical candidates:
   - Layer thicknesses (body, back protrusion, front protrusion depths)
   - Cylinder / box dimensions where the part has a clear semantic role (pin radius, slot width)
   - Polar-pattern centres when they should be on a model axis
   Polygon vertex coords (the `Pencil.draw(length, angle)` calls inside a body silhouette) usually stay literal — they describe the shape itself, not a tunable dimension. If the polygon clearly *should* be parametric (regular n-gon, tessellated circle), see step 9.

9. **Simplify mesh artefacts** where the algorithm preserved tessellation noise. Recurring cases (judgment calls — only apply when the value clearly looks like noise):
   - **n-gon → disc.** A high-vertex-count silhouette (e.g. 42-gon) approximating a circle should become `SmarterCone.cylinder(r, h)` or `SmarterCone.base(r).extend(height=h)`. The dispenser plate did this — see `dispenserbottlemount.py::create_diaphragm_plate`.
   - **Off-axis polar pattern → on-axis.** A polar pattern with a sub-mm centre offset from the natural axis is almost always tessellation noise — recentre on the model axis.
   - **42-gon body / 32-gon plate / 16-gon pin** — these vertex counts are emitted-from-circle giveaways.

10. **Re-verify after edits.** After parametrization and simplification, re-run the model's `__main__` and visually inspect the exported `.3mf` (`f3d models/<group>/<name>/export.3mf` or open `current_model.3mf` in F3D with `--watch`). If you have regression targets (bbox, volume), compare against the source mesh as `tests/sava/csg/build123d/reconstruct/test_iris_blade.py` does.

11. **Clean up.** Delete `tmp/reconstructed_<part>.py` once the model has absorbed it. Do NOT commit the intermediate emitted file.

## Reference

- `docs/code/reconstruct/README.md` — public API surface
- `docs/code/reconstruct/ALGORITHM.md` — pipeline + detection heuristics; read when extending the algorithm
- `docs/code/reconstruct/FINDINGS.md` — lessons from the iris-blade reference; read before debugging an unexpected reconstruction
- `src/sava/csg/build123d/models/other/dispenserbottlemount.py` — reference integration: `create_blade` (3-layer petal with back protrusion + pivot pin) and `create_diaphragm_plate` (n-gon → disc simplification)
- `tests/sava/csg/build123d/reconstruct/test_iris_blade.py` — regression-test pattern (bbox + volume comparison)

## Out of scope

- Reconstructing non-2.5D parts (lofts, free-form surfaces, multi-axis cylindrical features). The CLI aborts with a reason; report it and stop.
- Auto-parametrizing the lifted dimensions — choosing which literals become `dim.<field>` is a design decision the user needs to make case by case.
- Re-running reconstruction after edits. The emitted code is a one-shot starting point; treat the integrated, parametrized model as the source of truth from that point on.
