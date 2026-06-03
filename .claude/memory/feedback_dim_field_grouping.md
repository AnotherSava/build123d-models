---
name: feedback-dim-field-grouping
description: "Group Dimensions dataclass fields by the geometric piece that primarily owns them, even if other pieces consume them downstream"
metadata: 
  node_type: memory
  type: feedback
---

When organizing fields in a model's Dimensions dataclass under section comments (e.g. "Dispenser housing", "Iris diaphragm"), put each field with its PRIMARY OWNER — the geometric piece whose dimensions it most directly defines — not with the section that consumes it.

**Why:** During the dispenser-bottle-mount cleanup, `wall_padding` was originally placed in the "Dispenser support" section because it was added when wedge work was happening. But its only consumers were `plate_radius` (iris) and `create_cover` (iris cover) — never the support code. The user moved it to the iris section because the iris is what wall_padding sizes.

**How to apply:**
- For each field, ask: "If this dimension changed, which geometric piece would visibly change first?" That's its owner.
- Section headers should describe what each group of fields belongs to (e.g. "Dispenser support wedges + cut_holder tolerances"), not where they get used.
- Cross-cutting fields that don't fit a single piece (e.g. `above_dispenser_height` spans iris and dispenser) belong with the piece whose primary dimension they define; add an inline comment for context.
