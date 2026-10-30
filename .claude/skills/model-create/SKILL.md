---
name: model-create
description: Create new model based on build123d framework
disable-model-invocation: true
allowed-tools: Read, Write, Bash, Edit
---
1. Ask for model group and name if not provided as input (like "other"/"cable holder")

2. Create python file for the model. Group defines package under sava/csg/build123d/models (like sava/csg/build123d/models/other), model name defines the filename (like cableholder.py - no underscores)

3. Add required imports at the top of the file:
```python
from dataclasses import dataclass

from sava.csg.build123d.common.modelspec import ModelSpec, export_model
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartsolid import SmartSolid
```

4. Create dimensions class using CamelCase for class name, with length, width and height float fields with default values of 5.0, 4.0 and 3.0:
```python
@dataclass(frozen=True)
class CableHolderDimensions:
    length: float = 5.0
    width: float = 4.0
    height: float = 3.0
```

5. Create model class in the same file that takes and stores dimensions in constructor, with a method that creates and returns a SmartBox with length, width and height taken from dimensions fields:
```python
class CableHolder:
    def __init__(self, dim: CableHolderDimensions) -> None:
        self.dim = dim

    def create(self) -> SmartSolid:
        return SmartBox(self.dim.length, self.dim.width, self.dim.height)
```

6. Add a `build()` function returning a `ModelSpec`, and a main section exporting it. `export_model` writes the 3MF scene (`export.3mf`, also copied to the viewer's current model) and one STL per part under `stl/`. `name` is the model name in snake_case; `output_dir` is `models/<group>/<name>` — except where the group's existing models already export to a differently named folder, which wins (the `hydroponics` package exports to `models/hydroponic/`). Once the model has more than one part, pass the assembled parts as `scene` and the print-posed parts as `prints` (see `docs/code/model_regression.md` and `tray.py`):
```python
def build() -> ModelSpec:
    dimensions = CableHolderDimensions()
    cable_holder = CableHolder(dimensions)
    return ModelSpec(name="cable_holder", output_dir="models/other/cable_holder", scene=[cable_holder.create()])


if __name__ == "__main__":
    export_model(build())
```

7. Execute and see if output files are created.

8. Add python file to git using `git add <path>`

9. Create PyCharm run configuration by adding a new `<configuration>` block to `.idea/workspace.xml` inside the `<component name="RunManager">` section. Copy an existing Python configuration and update:
   - `name` attribute: model name in Title Case (e.g., "Cable holder")
   - `SCRIPT_NAME` option: module path (e.g., "sava.csg.build123d.models.other.cableholder")

   Then add `<item itemvalue="Python.<name>" />` (e.g. `Python.Cable holder`) to the `<list>` at the end of that same `RunManager` component, beside the other configurations' items.
