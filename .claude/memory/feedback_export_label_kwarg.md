---
name: Always pass `label` as keyword to exporter.export()
description: export() signature is export(*shapes, label=None); a positional 2nd arg gets treated as a shape and a string recurses infinitely
type: feedback
---
When calling `export()` from `sava.csg.build123d.common.exporter`, the label argument must be passed as a keyword: `export(blade, label="reconstructed")`.

**Why:** The signature is `export(*shapes, label: str = None)`. A positional second argument lands in `*shapes`, not in `label`. If it's a string, `_copy_shape_for_storage` sees it as `Iterable` (and not a build123d `Shape`) and recurses character-by-character — every char is itself an iterable 1-char string — until `RecursionError: maximum recursion depth exceeded`.

**How to apply:** Always use the keyword form anywhere `export()` is called with a custom label. The same rule extends by analogy to any other variadic-shapes API in this codebase (e.g. `SmartSolid.__init__(*args, label=None)`).

```python
# Correct:
export(blade, label="reconstructed")

# Incorrect — second arg is parsed as another shape:
export(blade, "reconstructed")
```
