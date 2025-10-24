# build123d-models

This project contains 3d models (mostly board game inserts) and helper tools for their creation based on the [build123d](https://github.com/gumyr/build123d) framework.

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Viewing 3D Models with F3D

This project uses [F3D](https://f3d.app/) as the recommended viewer for generated 3D models. It provides an opportunity to automatically reload model upon file changes. Having export operation as the last step of your script will let you see the changes after each execution:

```python
from sava.csg.build123d.common.exporter import Exporter

Exporter(model_to_export).export()
```

### Quick Start

A convenience `f3d.bat` batch file is provided at the project root:

```bat
f3d-console models\current_model.3mf --watch --opacity=0.6
```

It uses the following arguments:

- `models\current_model.3mf` - Path to the (default) model file to view
- `--watch` - Automatically reload the file when it changes
- `--opacity=0.6` - Set model transparency to 60% for better visibility
