Agent Guidelines for build123d-models

This file is reserved for project-specific agent guidelines. Add only the rules and notes you want enforced in this repository.

Guidelines

- Keep guidelines concise: prefer short, actionable rules and examples; avoid long rationale blocks where obvious.

- Each geometric model must include a `dimensions` data class (or equivalent) that defines every numeric measurement used to construct the model. No geometry constants should be hardcoded in construction code; reference `dim.<field>` instead.

- Preferred model orientation: `length` >= `width`.

Example (Python):

@dataclass
class MyModelDimensions:
    length: float = 100.0
    width: float = 50.0
    height: float = 25.0

def make_my_model(dim: MyModelDimensions):
    base = Box(dim.length, dim.width, dim.height)

- When writing unit tests, prefer parametrized tests over separate test functions for each input. Use `pytest.mark.parametrize` to test multiple inputs in a single test function:

```python
@pytest.mark.parametrize("input,expected", [
    (5, [5]),
    ([1, 2, 3], [1, 2, 3]),
    ([1, [2, 3], 4], [1, 2, 3, 4]),
    ("hello", ["hello"]),
])
def test_flatten(input, expected):
    assert list(flatten(input)) == expected
```

- Leave an empty line at the end of every file.

- Always run tests that were just created to verify they work correctly.

- Use the virtual environment Python interpreter (venv/Scripts/python.exe) for running tests and commands.

- Always specify parameter and return types in function definitions using Python type hints:

```python
def calculate_distance(point1: Vector, point2: Vector) -> float:
    return (point2 - point1).length

def create_boxes(count: int, size: float = 1.0) -> list[Box]:
    return [Box(size, size, size) for _ in range(count)]

def process_shapes(shapes: list[Shape], transform: bool = False) -> None:
    for shape in shapes:
        # process shape
        pass
```

## Import Organization

- **All imports MUST be at the top of the file**, immediately after module docstring and before any other code
- **NO inline imports** inside functions, methods, or classes unless absolutely necessary for specific technical reasons

Import order (following PEP 8) with blank lines between each group:
1. **Standard library imports** (`import os`, `from typing import List`)
2. **Third-party library imports** (`from build123d import Vector, Plane, Box`)
3. **Local application imports** (`from sava.common.common import flatten`)

Import style guidelines:
- Use `from module import name` for frequently used items
- Group related imports from the same module: `from build123d import Vector, Plane, Box, Axis, Location`
- All `build123d` imports should be at the top
- All `sava.*` imports should be at the top
- Remove redundant imports (same module imported multiple times)

Inline imports only allowed for:
- **Circular import resolution** - when moving to top would create circular dependencies
- **Conditional imports** - when import depends on runtime conditions
- **Performance-critical lazy loading** - when import is expensive and rarely used
- **Type checking only** - imports only needed for type hints
