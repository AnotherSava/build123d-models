---
name: model-dimensioned-draft
description: Create a dimensioned technical drawing (SVG) of a build123d model — cross-section, side view, detail callouts, all dimensions labelled
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Bash, Glob
---

Produces architectural-style dimensioned drawings of build123d models for design review, parametrization planning, or documentation. Output is an SVG file that can be viewed directly in IntelliJ, a browser, or any SVG viewer. The drawing uses the same conventions as the cable-channel reference (`models/other/cable_channel/dimensioned_drafts/cable_channel.py`): cross-section + side view + zoomed detail callouts, sub-dimensions stacked closer to the figure with the overall further out, hidden / cavity features as dashed red lines.

## Output layout

Each draft is committed alongside the model's other outputs:
```
models/<group>/<model_name>/
├── dimensioned_drafts/
│   ├── <draft_name>.py   # the drafting script (commits to repo)
│   └── <draft_name>.svg  # rendered SVG (commits)
├── export.3mf
└── stl/
```
For a single overview drawing, `<draft_name>` matches the model directory name (e.g. `cable_channel.py/.svg`). Add separate scripts for additional drafts (`<feature>_detail.py`, `assembly.py`, …) as needed.

## Context

- Recent model files: !`ls -t src/sava/csg/build123d/models/*/*.py 2>/dev/null | head -5`
- Drawing library: `.claude/skills/model-dimensioned-draft/scripts/draft_lib.py`
- Worked example: `models/other/cable_channel/dimensioned_drafts/cable_channel.py`

1. **Identify the model.** Take the top entry from **Recent model files** as the candidate. Confirm with the user before proceeding.

2. **Read the model's Python source** to pull dimension values and understand the geometry. Note the cross-section profile (the Pencil trace), feature placements, and any nested cut/fuse operations. If a `<Name>Dimensions` dataclass exists, use those values; otherwise extract literals from the `create` method.

3. **Plan the views with the user.** Propose a set tailored to the part. Typical defaults:
   - **Cross-section** (the most informative view — orthogonal to the extrusion axis, showing the full profile)
   - **Side view** (along the extrusion axis, showing length and any along-length features like end cavities, cuts, protrusions)
   - **Detail callout(s)** — zoomed views isolating small features (corner geometry, slope angles, snap-fit details) where the main view's scale makes them illegible
   For each view, decide the projection (XY / YZ / XZ), scale, and which dimensions to label.

4. **Write the drawing script** at `models/<group>/<model_name>/dimensioned_drafts/<draft_name>.py`, importing from the skill's `draft_lib`. Use the cable-channel worked example as a template:
   ```python
   import sys
   from pathlib import Path
   REPO_ROOT = Path(__file__).resolve().parents[4]  # adjust depth if needed
   sys.path.insert(0, str(REPO_ROOT / '.claude' / 'skills' / 'model-dimensioned-draft' / 'scripts'))
   from draft_lib import Drawing, View

   d = Drawing('<Model Name> — Dimensioned Draft', width=1000, height=800)

   # One View per projection. origin = SVG (x, y) that corresponds to mm (0, 0).
   cs = d.add_view(View(origin=(150, 440), scale=14,
                        title='Cross-section', title_pos=(290, 200)))
   cs.path([(0,0), (20,0), (20,12.9), (0,12.9)])  # body polygon
   cs.dim_h(v_at=12.9, u1=0, u2=20, label='20  (width)', side='above', offset_px=14)
   ...

   if __name__ == '__main__':
       out_path = Path(__file__).parent / '<draft_name>.svg'
       d.save(str(out_path))
   ```
   Mirror the cable-channel layout: cross-section on the left, side view at the bottom, detail callouts to the right.

5. **Style conventions** (the lib applies defaults that match these — override only when needed):
   - Body fill: `#dde3ea`, outline: `#1f2933`, line weight 0.9
   - Hidden / cavity features: dashed red (`#c0392b`, `stroke-dasharray="4,3"`)
   - Dimension extension lines: `#666`, 0.5 px (thin)
   - Dimension line: `#222`, 0.8 px with arrows at both ends
   - Sub-dimensions stack at `offset_px=14..16`; overall dimensions at `offset_px=36..60`
   - Title above each view in 14 pt bold; main title 20 pt; subtitle `all dimensions in mm`
   - Vertex letter labels (A, B, C, …) — when tagging polygon corners so model code can reference them: place each letter along the bisector of the **wider** angle at that vertex. For a CCW polygon, that's the **exterior** bisector at convex vertices (interior < 180°, polygon "bumps out") and the **interior** bisector at concave vertices (interior > 180°, polygon "indents"). Offset ~0.3 mm out from the corner, size ~6 pt, and pass `baseline='central'` to `view.text()` so the letter's geometric centre sits on the bisector point (not its alphabetic baseline). The interior-bisector direction at vertex P is `unit(perp_left(e_in) + perp_left(e_out))` where `perp_left((a,b)) = (-b, a)`; concave uses it, convex uses its negation. Worked example: cable-channel cross-section labels A–H.

6. **Render SVG and review.** Run the script (`venv/Scripts/python.exe models/<group>/<model_name>/dimensioned_drafts/<draft_name>.py`); it writes the SVG next to the script. Open the SVG in IntelliJ, a browser, or any SVG viewer. Common issues:
   - Title overlap with topmost dimension labels (fix with `title_pos` overrides)
   - Dimension labels colliding (stagger `offset_px`, or use different `side`)
   - Detail callouts going off-screen when their mm origin is far from (0,0) (set `View.origin` so `(svg_x = origin[0] + visible_mm * scale)` lands in-canvas; pair with `title_pos` because `title_y_offset` won't work)
   - **Views intersecting other views.** Each view's "bounding box" includes figure + dim labels + footer annotations + title text + axis indicator (extends ~25 px above the title's baseline). When adding a new view below an existing one, account for the lower view's axis indicator above its title (`arm + label height ≈ 28 px`).
   - **Padding ratio rule.** Padding between adjacent views (including their headers and axis indicators) must be **at least 2× the title-to-top-element padding within each view**. With a typical title-to-top of ~18 px, inter-view padding should be ≥ 36-40 px. Verify by computing the relevant edges: e.g., corner-detail-footer-y → rim-detail-axis-top-y for vertically-stacked views in the same column.
   - **Text comments intersecting dim arrows/labels within the same view.** Annotations placed near figure edges (`dx`/`dy` shifts on `view.text()`) can collide with dim lines/labels on the same side. Two fixes: (a) place the annotation INSIDE the body fill (typically clears dims since dims sit outside the figure) — pick coordinates so the annotation also clears any feature lines like slopes; (b) shift `dy` further until the annotation drops below the lowest dim label on that side.
   - **View title overlapping the top dim label.** The top dim label sits at `figure_top_svg_y - offset_px`. If the title baseline is too close to that label's top, they collide. Aim for ≥ 15 px between the title baseline and the top dim label's top edge. To fix, push the figure DOWN by adjusting `View.origin[1]` (with `flip_y=True`, increasing origin_y moves the figure down) until the gap opens up — don't try to fight it via `offset_px`, since `offset_px` controls figure-to-dim spacing and shrinking it just moves the label into the figure.

7. **Iterate with the user.** Ask the user to open the SVG; take feedback on labels, scale, missing dimensions, layout. Re-run the script.

8. **Commit.** Both files (`.py`, `.svg`) in `dimensioned_drafts/` go into the repo with the model — they're outputs of the model just like `export.3mf` and the STLs.

## Reference

- `scripts/draft_lib.py` — `Drawing` + `View` classes; `View.path/line/rect/text/dim_h/dim_v` are the building blocks
- `models/other/cable_channel/dimensioned_drafts/cable_channel.py` — worked example: 3 views (cross-section, corner detail, side view), sub-dims + overall dims on each axis, hidden-feature callout

## Out of scope

- Auto-extracting dimensions from the model — the agent must read the model source and choose which numbers to label. Auto-discovery would require a model-introspection layer beyond what the lib provides.
- 3D / isometric views — the lib is 2D. For 3D inspection use F3D (`f3d models/<group>/<name>/export.3mf`).
- Editing the model from the drawing — drawings are read-only output. Parametrization changes go through the `model-reconstruct` skill or by editing the model directly.
