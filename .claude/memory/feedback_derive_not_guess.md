---
name: feedback-derive-not-guess
description: Derive geometric values from object sizes/angles analytically; never introduce magic tuning factors
metadata: 
  node_type: memory
  type: feedback
---

When computing a geometric relationship (rotation angle to align two features, perpendicular distance, intersection point, tracking factor between two motions, etc.), derive the value analytically from the object's sizes and angles. **Don't introduce magic interpolation constants** like `TRACKING = 0.5` to make behavior "look about right".

**Why:** During iris cover-rotation alignment, I picked `TRACKING = 0.5` as a half-tracking heuristic between full pin-tracking and a fixed cover. The user responded "I don't want to guess the constant value, just calculate it based on object sizes and angles." The correct answer turned out to be a clean closed-form derivation: cover rotation `R = pin_polar + asin(D / pin_r) - theta_L` where `D` is the perpendicular distance from cover origin to the stadium long axis (computed from the stadium's local position + orientation). No magic constant needed.

**How to apply:**
- If tempted to write `MAGIC_FACTOR = 0.5` (or similar), stop and identify the actual geometric relationship: line equations, projections, perpendicular distances, intersection points.
- Solve the geometry on paper / mentally first. Express the result as a formula in the object's existing dimensions, not a tuning knob.
- Constants like `stadium_long_local`, `pin_radius`, `slot_length` etc. are fine — they're inputs to the geometry. What's NOT fine is an arbitrary blend factor between two behaviors.
- Verify the formula by sampling the actual geometry at extremes and checking the constraint (e.g., "pin perpendicular distance to stadium line is exactly 0 at every slot_position").
