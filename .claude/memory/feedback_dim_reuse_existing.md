---
name: feedback-dim-reuse-existing
description: "When moving local constants into the model's Dimensions dataclass, first check if an existing field represents the same concept (possibly with a different name) and reuse it"
metadata: 
  node_type: memory
  type: feedback
---

When the user asks to "move to dimensions" (or similar), audit each local constant against existing fields BEFORE adding a new one. If the same concept is already in the dataclass under a slightly different name, reuse the existing field instead of creating a duplicate.

**Why:** The user explicitly stated this rule: *"move to dimensions unless they are already there (might be with a slightly different name - in this case reuse)"*. Duplicate fields drift apart over time and obscure which one is the source of truth.

**How to apply:** For each local constant, map it to an existing field by semantic meaning. Examples from the dispenser bottle mount refactor:
- `blade_height = 10.0` → reused existing `blade_thickness`
- `cut_angle = 10` → reused existing `cut_angle` (same name)
- `cut_length = 5 - tight_padding` → reused existing `cut_length`, derived inline
- `wall_thickness = 2` → reused existing `thickness_wall`
- `cover_outer_diameter = 76` → reused existing `dispenser_outer_diameter`

When the local is a computed value (e.g., `blade_height + blade_vertical_padding`), add a derived @property on the dataclass rather than a stored field. See also [[feedback_derive_not_guess]].
