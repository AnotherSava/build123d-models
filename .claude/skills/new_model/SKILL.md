---
name: new_model
description: Create new model based on build123d framework
disable-model-invocation: true
allowed-tools: Read, Write, Bash, Edit
---
1. Ask for model group and name if not provided as input (like "other"/"cable holder")

2. Create python file for the model. Group defines package under sava/csg/build123d/models (like sava/csg/build123d/models/other), model name defines the filename (like cableholder.py - no underscores)

3. Add required imports at the top of the file:
```python
from dataclasses import dataclass

from sava.csg.build123d.common.exporter import export_3mf, export_stl
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
    def __init__(self, dim: CableHolderDimensions):
        self.dim = dim

    def create(self) -> SmartSolid:
        return SmartBox(self.dim.length, self.dim.width, self.dim.height)
```

6. Add main section that creates a dimensions object, model object, solid and exports it both to 3mf and stl (use model group and snake_case in model folder path):
```python
if __name__ == "__main__":
    dimensions = CableHolderDimensions()
    cable_holder = CableHolder(dimensions)
    model = cable_holder.create()
    export_3mf("models/other/cable_holder/export.3mf", model)
    export_stl("models/other/cable_holder/stl", model)
```

7. Execute and see if output files are created.

8. Add python file to git using `git add <path>`

9. Create PyCharm run configuration by adding a new `<configuration>` block to `.idea/workspace.xml` inside the `<component name="RunManager">` section. Copy an existing Python configuration and update:
   - `name` attribute: model name in Title Case (e.g., "Cable holder")
   - `SCRIPT_NAME` option: module path (e.g., "sava.csg.build123d.models.other.cableholder")
