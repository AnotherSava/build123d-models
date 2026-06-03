---
name: feedback-nested-dim-classes
description: "Extract a coherent dim cluster (4+ fields, or any group used in 2+ places) into a nested @dataclass; instantiate from the outer dim class's __post_init__ a la stand.py"
metadata: 
  node_type: memory
  type: feedback
---

When a model's `Dimensions` dataclass has a tight cluster of related fields — especially if the same cluster shows up more than once on the model (e.g. one set for a cover gear, another for a support gear) — extract that cluster into its own dataclass and compose via the outer dim class's `__post_init__`.

**Why:** The user pushed for this after I had 9 `support_gear_*` + `cover_gear_*` fields cluttering `DispenserBottleMountDimensions`. Pulling them into a `GearDimensions` class made the gear's API obvious, let the two instances (`cover_gear`, `support_gear`) share semantics without duplicate field naming, supported clean per-instance overrides, and kept cross-field derivations (gear `thickness` derived from `cover_thickness` etc.) in one place. The pattern is already established in this project — `src/sava/csg/build123d/models/hydroponics/stand.py`'s `StandDimensions` composes `HandleDimensions`, `HoseConnectorDimensions`, `PipeDimensions`, `TubeEtchesDimensions`, `HoseHolder` the same way.

**How to apply:**

When to extract a sub-dimensions class:
- A coherent cluster of **4+ related fields** (gear, hose connector, etches, …).
- A cluster **used in 2+ places** on the same model (`cover_gear` and `support_gear` share `GearDimensions`).
- A cluster with **internal cross-derivations** that would be hard to maintain inline.

How to wire it up (the `stand.py` pattern):

1. **Inner dataclass:** `@dataclass` (NOT `frozen=True`). Required fields first (no defaults), then defaults. Document semantics in a class docstring.

2. **Outer dataclass:** also `@dataclass` (not frozen). Each nested instance is a field defaulting to `None`:
   ```python
   cover_gear: GearDimensions = None
   support_gear: GearDimensions = None
   ```

3. **`__post_init__`** instantiates missing instances with derived values, passing them straight to the constructor:
   ```python
   def __post_init__(self):
       self.cover_gear = self.cover_gear or GearDimensions(
           gear_count=48,
           thickness=self.cover_thickness,
           radius=self.dispenser_outer_radius,
       )
       self.support_gear = self.support_gear or GearDimensions(
           gear_count=16,
           thickness=self.above_dispenser_height - self.cover_thickness,
           radius=self.dispenser_outer_radius - self.cover_gear.radius_extra / 2,
       )
   ```

4. **Don't** post-process with per-field `if x is None: x = ...` checks — pass derived values to the constructor directly. The `or` already gives callers the override path, and partial overrides aren't worth the complexity (a `GearDimensions` without thickness/radius is meaningless anyway, so make them required fields).

5. **Order matters** in `__post_init__` when one nested instance depends on another (here `support_gear.radius` reads `cover_gear.radius_extra`). Initialize the dependency first.

6. **Update the consumer:** the method that builds geometry should take the dataclass as a single parameter rather than splaying its fields. `create_gear(gear: GearDimensions)` is cleaner than `create_gear(count, thickness, radius, sharpness, …)`.

**Trade-off the pattern accepts:** if a caller passes a complete nested instance, top-level dim changes won't auto-cascade into it (e.g. setting `cover_thickness=3` won't update a user-provided `cover_gear.thickness`). This is the right behavior — explicit overrides should beat derivation — and matches what `stand.py` does.

See also: [[feedback_dim_reuse_existing]], [[feedback_dim_field_grouping]].
