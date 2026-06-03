---
name: Separate independent objects when exporting for comparison
description: When exporting multiple unrelated shapes in one 3MF/STL (source vs reconstructed, before vs after, variants), translate them so their bounding boxes don't overlap
type: feedback
---
When exporting more than one independent object into the same file for visual comparison, translate each so their bounding boxes are clearly separated — don't let them intersect or overlap in space.

**Why:** Overlapping geometry is unreadable in F3D / 3MF viewers even with `--opacity`. Z-fighting hides one shape behind another, and intersections make it impossible to see which feature belongs to which object. The whole point of side-by-side export is visual comparison, which fails when the shapes occupy the same volume.

**How to apply:**
- Before `export(...)` of multiple independent labels, compute each shape's bounding box and offset them so they sit clearly apart — typically shift by `bbox_width + gap` along the X (or longest) axis.
- A 5–20% gap relative to the shape size is usually enough. Aim for the close end (~10%) so features stay easy to compare; bigger gaps force the viewer to pan back and forth. The shift is `bbox_width × 1.1`, NOT a flat hundreds-of-mm offset.
- This applies only to *independent* objects shown for comparison. Genuine assemblies (parts that belong together) should stay in their real relative positions.
- Example pattern:
  ```python
  bb = source.solid.bounding_box()
  size_x = bb.max.X - bb.min.X
  reconstructed.move(size_x * 1.1, 0, 0)  # shift right by 110% of width
  export(source, label="source")
  export(reconstructed, label="reconstructed")
  ```
