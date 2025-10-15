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
