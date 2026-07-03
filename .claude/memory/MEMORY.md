# Project Memory

## Publishing Scripts
- All technical details are in `.claude/skills/model-publish/PUBLISHING_NOTES.md` (checked into repo)
- Skill: `.claude/skills/model-publish/SKILL.md` — 10 steps from source code reading to publishing
- Scripts: `.claude/skills/model-publish/scripts/` — `web_search.py`, `thingiverse.py`, `makerworld.py`
- First published model: marker_holder ([Thingiverse](https://www.thingiverse.com/thing:7294115), [MakerWorld](https://makerworld.com/en/models/drafts/6798386))

# Environment
- Virtual env: `venv/Scripts/python.exe`

# Projects
- [project_iris_diaphragm.md](project_iris_diaphragm.md) — Iris diaphragm mechanism: reference STL analysis, mechanism research, InverseCSG tool info

# Reference
- [reference_alignment_builder_defaults.md](reference_alignment_builder_defaults.md) — `align()` chain silently re-centres any axis not explicitly set via `.x()/.y()/.z()`
- [reference_smartsolid_invariant.md](reference_smartsolid_invariant.md) — Two SmartSolid invariants (origin/location, _orientation/solid.orientation); _reanchor + _apply_tracked_transforms restore after ops
- [reference_arrange_scene_pattern.md](reference_arrange_scene_pattern.md) — Multi-part export: assembled 3MF scene first, then `clear()`, then STL (applies `bed_orientation`); tray.py/splitter.py are the correct examples
- [reference_slice_verification.md](reference_slice_verification.md) — Verify geometry: thin-Box slices, refactor equivalence (volume/bbox, relative tolerances), intersect-volume fit checks
- [reference_extrude_winding_direction.md](reference_extrude_winding_direction.md) — extrude(face, h) follows the face normal, which flips with polygon winding; position cutter prisms by recentering, never by assuming +normal
- [reference_forward_port_stale_model.md](reference_forward_port_stale_model.md) — Port a stale model forward: run its last-working commit as a golden oracle (worktree + current venv), diff per sub-part to localize each common-API drift; documents Pencil/SweepSolid/rotate semantic changes

# Feedback
- [feedback_visualization_orientation.md](feedback_visualization_orientation.md) — Build models in scene/visualization orientation, NOT print; use `SmartSolid.bed_orientation` for print pose (applied only at STL export). Reverses the old "build in print orientation" guidance
- [feedback_skill_paths.md](feedback_skill_paths.md) — Use skill base directory from prompt header, don't search
- [feedback_assert_in_property.md](feedback_assert_in_property.md) — Validate derived values via assert in the property (point of use), not __post_init__; bare-minimum message for non-customer-facing code
- [feedback_export_default_location.md](feedback_export_default_location.md) — When user asks to export, save to default `models/current_model.3mf`, not `tmp/`
- [feedback_single_line_constructors.md](feedback_single_line_constructors.md) — Prefer single-line constructor calls (even long ones) over multi-line argument formatting
- [feedback_emit_idiomatic_style.md](feedback_emit_idiomatic_style.md) — Build CAD in default Plane.XY, single end-transform; hand-written code mirrors emit ops
- [feedback_build_at_origin_then_align.md](feedback_build_at_origin_then_align.md) — Build a part simply at the origin, then place it with the `align...` family relative to other parts; don't bake target coords into a Plane origin / Pencil start
- [feedback_no_redundant_self_params.md](feedback_no_redundant_self_params.md) — Don't pass a class's own fields (self.dim.*) into its methods; read from self, pass only what varies per call
- [feedback_create_method_naming.md](feedback_create_method_naming.md) — Name model-building methods create_*/_create_*; mutating/action methods keep a verb (e.g. _apply_connector)
- [feedback_separate_comparison_exports.md](feedback_separate_comparison_exports.md) — When exporting independent shapes for comparison, translate them so bounding boxes don't overlap
- [feedback_export_label_kwarg.md](feedback_export_label_kwarg.md) — Always pass `label` as keyword to `export()`; positional 2nd arg recurses infinitely on string
- [feedback_derive_not_guess.md](feedback_derive_not_guess.md) — Derive geometric values from object sizes/angles; never introduce magic tuning factors
- [feedback_dim_reuse_existing.md](feedback_dim_reuse_existing.md) — When moving local constants into a model's Dimensions dataclass, reuse existing fields with matching meaning instead of adding duplicates
- [feedback_dim_field_grouping.md](feedback_dim_field_grouping.md) — Group Dimensions fields by primary owner (the piece whose geometry they define), not by where they're consumed downstream
- [feedback_nested_dim_classes.md](feedback_nested_dim_classes.md) — Extract a coherent dim cluster (4+ fields, or any group used in 2+ places) into a nested @dataclass; instantiate from outer __post_init__ a la stand.py
- [feedback_diff_against_draft.md](feedback_diff_against_draft.md) — On model/draft mismatch reports, diff feature-by-feature (corner convexity!); generic metrics that already passed can't catch it
- [feedback_draft_rules_as_automation.md](feedback_draft_rules_as_automation.md) — Implement quantitative draft layout rules as draft_lib automation (bounds → auto-layout), never as guidance + per-draft tuning
- [feedback_draft_first_model_changes.md](feedback_draft_first_model_changes.md) — On model-change requests, update and review the dimensioned draft FIRST, then implement the model
