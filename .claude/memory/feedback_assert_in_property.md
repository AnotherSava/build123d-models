---
name: assert-in-property
description: "For internal validation, use asserts in properties at the point of use rather than __post_init__ checks"
metadata: 
  node_type: memory
  type: feedback
---

For internal validation in frozen dataclasses (e.g. checking that a derived property meets a minimum), use `assert` inside the property at the point of use rather than `__post_init__` with `if … raise ValueError(...)`.

**Why:** This code is not customer-facing. The error message just needs enough information to diagnose the bug — a bare-minimum assert is enough.

**How to apply:**
- Compute the value in the property, then assert it.
- One-line message with the actual value and the constraint: `assert value >= minimum, f"X too short ({value}) for Y"`.
- Don't construct verbose multi-line ValueErrors with formatting, recomputed minimums, or "set field X >= Y" hints.
