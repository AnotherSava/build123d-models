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

   d = Drawing('<Model Name>')  # subtitle defaults to 'Dimensioned Draft (mm)'; canvas auto-sizes

   # One View per projection. origin = authored (x, y) that corresponds to mm (0, 0) —
   # page placement is automatic (View.row groups views into page rows), so origin only
   # needs to be consistent within the view. The header auto-centers over the content.
   cs = d.add_view(View(origin=(150, 440), scale=14, title='Cross-section', axis_labels=('Y', 'Z')))
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
   - Main title 20 pt = just the model/feature name; subtitle (11 pt) defaults to `Dimensioned Draft (mm)`
   - View headers (14 pt bold title + axis hint) are placed by the lib: centred horizontally over the view's tracked content bounds (figure + dims + labels), `TITLE_PAD` (18 px) above the topmost element, with a fixed `TITLE_AXIS_GAP` (5× the header word spacing, AFM-measured) between title and axis hint
   - Axis hints follow the F3D colour convention: X red, Y green, Z blue (`AXIS_COLORS` in the lib)
   - Derive dimension-label values from the script's design constants with f-strings (`f'{2 * (TIP_HALF - LEAD_IN):g} tab bottom'`), never hardcode the numbers in label strings — drafts get retuned, and literal labels silently go stale
   - Vertex letter labels (A, B, C, …) — when tagging polygon corners so model code can reference them: place each letter along the bisector of the **wider** angle at that vertex. For a CCW polygon, that's the **exterior** bisector at convex vertices (interior < 180°, polygon "bumps out") and the **interior** bisector at concave vertices (interior > 180°, polygon "indents"). Offset ~0.3 mm out from the corner, size ~6 pt, and pass `baseline='central'` to `view.text()` so the letter's geometric centre sits on the bisector point (not its alphabetic baseline). The interior-bisector direction at vertex P is `unit(perp_left(e_in) + perp_left(e_out))` where `perp_left((a,b)) = (-b, a)`; concave uses it, convex uses its negation. Worked example: cable-channel cross-section labels A–H.
   - Letters identify **model points, not view annotations**: when the same physical point (or the edge it projects to) is visible in several views of the page — different projections included — label it with the same letter in each view. When two lettered edges project onto the same line in a view, combine them (`V/X`). Across related drafts of one model, keep letters globally unique (the puzzle-connector draft continues the cross-section's A–H with J–X) so a letter reference is unambiguous in conversation.

6. **Verify non-trivial outlines against the model.** When a view projects an intricate 3D region — mitred corner joints, overlapping laps, anything where multiple seams meet or a leg was built in a rotated frame — do not hand-derive the silhouette from a mental projection. Compute it from the built solid: intersect the model with a thin Box slab aligned to the view's projection and read the section's vertices, then check every draft outline vertex against that list. Mental projections of rotated-frame geometry are exactly where drafts go wrong (the corner_channels outer-corner notch took three correction rounds — wrong tab side, missing notch, V instead of W — that one slice section would have caught up front).

7. **Render SVG and review.** Run the script (`venv/Scripts/python.exe models/<group>/<model_name>/dimensioned_drafts/<draft_name>.py`); it writes the SVG next to the script. **Self-review before showing the user**: render the SVG to PNG via headless Chrome and Read the image to catch layout collisions yourself —
   ```powershell
   $chrome = @("$env:ProgramFiles\Google\Chrome\Application\chrome.exe", "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
   & $chrome --headless --disable-gpu --screenshot="$env:TEMP\<draft_name>.png" --window-size=<W>,<H> --default-background-color=FFFFFFFF "file:///<abs-path-to-svg>"
   ```
   (read `--window-size` from the `width`/`height` attributes on the generated SVG's root element — the canvas auto-sizes; delete the PNG when done). Fix what you spot, re-render, re-screenshot.

   **Layout is automated by the lib.** Each view tracks the bounds of everything it draws (figure, dims, labels); the header (title + axis hint) is centred over those bounds, `TITLE_PAD` (18 px) above the topmost element, with `TITLE_AXIS_GAP` (5× the header word spacing, AFM-measured) between title and axis hint. `Drawing.to_svg` then arranges whole view blocks: `View.row` groups views into page rows (add order within a row), rows are centred and stacked exactly `2 × TITLE_PAD` apart below the page header, views within a row sit `2 × TITLE_PAD` apart, and the canvas auto-sizes to the content. `View.origin` therefore only anchors the view's own mm coordinates — it does not control page placement. What remains manual: per-view content (dims, footers) and row assignment.

   Common issues:
   - Dimension labels colliding (stagger `offset_px`, or use different `side`)
   - **Long title on a narrow view.** The auto-centred header widens the block when the title is wider than the content — shorten the title and move detail into a footer note.
   - **Footers spreading past the block.** Free-text labels relate to the *whole* view block: left-align them with the outermost dim ladder (or centre under the block) and keep them within the view's span — long notes split into multiple lines.
   - **Text comments intersecting dim arrows/labels within the same view.** Annotations placed near figure edges (`dx`/`dy` shifts on `view.text()`) can collide with dim lines/labels on the same side. Two fixes: (a) place the annotation INSIDE the body fill (typically clears dims since dims sit outside the figure) — pick coordinates so the annotation also clears any feature lines like slopes; (b) shift `dy` further until the annotation drops below the lowest dim label on that side.

8. **Iterate with the user.** Ask the user to open the SVG; take feedback on labels, scale, missing dimensions, layout. Re-run the script.

9. **Commit.** Both files (`.py`, `.svg`) in `dimensioned_drafts/` go into the repo with the model — they're outputs of the model just like `export.3mf` and the STLs.

## Reference

- `scripts/draft_lib.py` — `Drawing` + `View` classes; `View.path/line/rect/text/dim_h/dim_v` are the building blocks, `fillet_polyline` rounds profile corners, layout (headers, rows, canvas) is automatic
- `models/other/cable_channel/dimensioned_drafts/cable_channel.py` — worked example: cross-section with vertex labels + zoomed rim detail, sub-dims + overall dims on each axis, constants-derived geometry and labels
- `models/other/cable_channel/dimensioned_drafts/puzzle_connector.py` — worked example: four views (top, mated schematic, side, zoomed section) across two rows, f-string labels

## Out of scope

- Auto-extracting dimensions from the model — the agent must read the model source and choose which numbers to label. Auto-discovery would require a model-introspection layer beyond what the lib provides.
- 3D / isometric views — the lib is 2D. For 3D inspection use F3D (`f3d models/<group>/<name>/export.3mf`).
- Editing the model from the drawing — drawings are read-only output. Parametrization changes go through the `model-reconstruct` skill or by editing the model directly.
