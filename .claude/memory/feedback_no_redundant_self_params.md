---
name: feedback_no_redundant_self_params
description: "Don't pass a class's own fields (e.g. self.dim.*) into its methods as parameters — read them from self inside; pass only the values that vary between calls"
metadata: 
  node_type: memory
  type: feedback
---

When a method belongs to a class that already holds the data, don't pass that data in as arguments. Read it from `self` inside the method, and let the parameter list carry **only what varies between calls**.

**Why:** redundant parameters bloat the signature and every call site, and they hide the signal — the reader can't tell at a glance what actually differs from one call to the next. A short signature of just the varying inputs makes the intent obvious.

**How to apply:** e.g. `_dovetail(taper_dir, clearance=0)` on `CableChannel` reads `lock_root_half` / `lock_tip_half` / `lock_protrusion` from `self.dim` itself; the only things that differ between the tab and the socket are the taper direction and the clearance, so those are the only parameters. Before: `_dovetail(out_dir, dim.lock_root_half, dim.lock_tip_half, dim.lock_protrusion)` (and again with `+ clearance` for the socket) — same fields threaded through redundantly.

Naturally complements [[feedback_build_at_origin_then_align]] (build simply, position by relation, not by threaded coordinates).
