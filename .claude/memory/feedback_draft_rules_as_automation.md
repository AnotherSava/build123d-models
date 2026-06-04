---
name: feedback-draft-rules-as-automation
description: Implement quantitative draft layout rules as enforced draft_lib automation, not skill guidance plus per-draft tuning
metadata:
  type: feedback
---

When the user states a quantitative layout/style rule for dimensioned drafts (padding ratios, fixed gaps, alignment, colours), implement it as **enforced automation in `draft_lib`** — bounds tracking → auto-placement → auto-sized canvas — not as SKILL.md guidance plus hand-tuned `View.origin` / `title_pos` values.

**Why:** guidance drifts the moment any draft is edited; automation cannot drift. On 2026-06-04 the "inter-block padding = 2× header padding" rule was first written into the skill as a checklist item and the gaps still came out wrong and inconsistent; it only actually held once `Drawing.to_svg` measured each view block and laid out rows itself. Same arc for the title→axis gap (estimate → AFM-measured, see the svg-text-metrics learning) and header centering. This is the drafting instance of "eliminate the bug class": manual spacing *is* the bug class.

**How to apply:** a new layout rule goes into `draft_lib`'s layout pass (`_track`/`_header_parts`/`to_svg`); draft scripts only declare content, `row` assignment, and mm geometry. If a rule seems to need per-draft pixel tuning, that's the signal the lib is missing a capability.

Related: [[reference-slice-verification]]
