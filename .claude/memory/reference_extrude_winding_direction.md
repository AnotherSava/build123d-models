---
name: extrude-winding-direction
description: "build123d extrude(face, h) follows the face normal, whose sign depends on polygon winding — never assume +z_dir of the construction plane"
metadata: 
  node_type: memory
  type: reference
---

Extruding a `Pencil`/wire-built face with `extrude(face, height)` goes along the **face normal**, and that normal flips with the polygon's winding (CCW in the plane → +z_dir, CW → -z_dir). A cutter prism positioned by "extrude then shift along +plane-normal" silently lands on the wrong side for CW polygons and cuts nothing.

**How to apply:** position such prisms by *recentering on the target* along the normal axis (compare bbox projections of prism vs target and move by the difference), as `SmartSolid._create_cut_prism` and `cablechannel._create_corner_prism` do — never by assuming the extrusion direction. Symptom of getting it wrong: boolean cut/intersect is a silent no-op (volume unchanged).
