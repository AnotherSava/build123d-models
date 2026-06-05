---
name: feedback-draft-first-model-changes
description: When changing a model that has a dimensioned draft, update and review the draft first, then implement the model change
metadata:
  type: feedback
---

**Draft first, then model.** When changing a model that has a dimensioned draft, update and review the draft FIRST (render, show the user, get approval), then implement the model change.

**Why:** The draft is the cheap medium for agreeing on geometry — iterating on a 2D SVG catches misunderstandings (wrong side, wrong cut shape) before expensive CAD and verification work. Established on the cable-channel wall-scarf change ("let's review dimensioned draft first before changing the model itself") and followed successfully for the outer-corner chamfer: DD approved, then `bend_down` reworked with slice verification.

**How to apply:** On any model-change request for a model with files under `models/<group>/<name>/dimensioned_drafts/`, edit the draft script, re-render the SVG, self-review the PNG, and present it before touching the model source. Carry the approved draft values into the implementation and verify the built solid against them (slice sections).

Related: [[feedback_diff_against_draft]], [[feedback_draft_rules_as_automation]]
