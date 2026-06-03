---
name: reference-alignment-builder-defaults
description: "AlignmentBuilder defaults uncalled axes to Center, silently re-centring on target"
metadata: 
  node_type: memory
  type: reference
---

When chaining `SmartSolid.align(target).<axis>(...)`, any axis NOT explicitly configured defaults to `Alignment.C` (centered on target). Observed during iris pin alignment:

```python
pin.align(blade).y(Alignment.LR).z(Alignment.RR)  # pin.x_centre = blade.x_mid (NOT pin's original X!)
```

**Why:** AlignmentBuilder applies a default center alignment to every axis unless overridden by `.x()`/`.y()`/`.z()`. This is invisible from the chain itself — there's no `.x(...)` so it *looks* like X is left alone, but it isn't.

**How to apply:**
- When porting code from `.move(dx, dy, dz)` to `.align(target).y/.z`, the unchained axis is NOT preserved — it gets re-centered on `target`. If the existing X (or whatever axis you skipped) position matters, the chain must explicitly set it.
- Symptom that bit me: pin axis position in iris frame shifted by 0.6 mm in X when switching from `pivot_pin.move(_PIVOT_U, _PIVOT_V, ...)` to `pivot_pin.align(blade).y(LR).z(RR)`. Cause: `body.x_mid = -4.39`, `_PIVOT_U = -3.78`, delta = 0.6 mm — the default center re-anchored the pin to body mid-X.
- See [[feedback-derive-not-guess]] for the related lesson that downstream formulas (`_aligned_cover_rotation`) had to be updated to match the new pin axis after this shift.
