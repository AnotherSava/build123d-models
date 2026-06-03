---
name: feedback_create_method_naming
description: "Name methods that build and return a model object create_* (or _create_* if private), matching the project convention; methods that mutate/act keep a descriptive verb"
metadata: 
  node_type: memory
  type: feedback
---

A method that **builds and returns a model object** should be named `create_*` (or `_create_*` when private), matching the established project convention: `create_channel`, `create_cap`, `create_straight`, `create_corner_right`, `_create_dovetail`. The `create` prefix signals "this returns a new object."

A method that **mutates or performs an action** (returns `None`, modifies a passed-in solid, applies an operation) keeps a plain descriptive verb — e.g. `_apply_connector(channel, out_dir)` fuses the connector onto `channel` in place, so it is not a `create_`.

**Why:** consistent factory naming makes the codebase scannable — you can tell at a glance which calls produce a new part versus which mutate state. Don't name a factory with a bare noun (`_dovetail`); name it `_create_dovetail`.
