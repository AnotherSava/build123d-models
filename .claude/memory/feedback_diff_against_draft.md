---
name: feedback_diff_against_draft
description: "When the user reports a model/draft mismatch, diff the two feature-by-feature (corner convexity, taper direction) — don't re-verify with generic metrics that already passed"
metadata:
  node_type: memory
  type: feedback
---

When the user reports that the model doesn't match the dimensioned draft, **diff the two feature-by-feature** instead of re-verifying with generic metrics that already passed. "Rounded" is not a sufficient check — the *direction* of each fillet matters (convex/outward on external corners vs concave/inward on internal corners), as does taper direction, offsets, and which feature sits on which side.

**Why:** in the cable-channel session the dovetail fillet was declared "correct" three times based on proxy measurements (section turn-angles, edge lists, interference volume) while the actual mismatch — all four tab corners rounded outward instead of the root corners rounding inward — was visible by eye-comparing the render to the draft. The user had to spell out the difference ("external corners are rounded outwards, while internal corners are rounded inwards"). Turn-angle metrics cannot distinguish convex from concave rounding, so they kept "passing" on wrong geometry.

**How to apply:** render the model in the same view as the draft (top-down for a floor-plan draft, orthographic-ish camera) and walk the outline corner by corner: same corner present? same convexity? same relative size? Only after identifying *what* differs reach for numeric verification of that specific property. Related global memory: [[feedback_verify_symptom_not_proxy]].
