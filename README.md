# build123d-models

This project contains 3D models (board game inserts, hydroponic and home improvements) and helper tools for their creation based on the [build123d](https://github.com/gumyr/build123d) framework.

## High-Level Utilities

The project includes a set of high-level wrapper classes that simplify common 3D modeling operations with build123d:

- **SmartSolid** - Primary wrapper around build123d shapes with fluent API for transformations, alignment system, and bound box helpers
- **SmartBox** - Box primitive with cutout operations and tapered walls support
- **SmartSphere** - Sphere primitive with hollow interior and shell creation
- **SmarterCone** - Cone/cylinder primitive with shell and offset methods
- **Pencil** - 2D drawing tool for creating complex profiles via lines and arcs, then extruding/revolving into 3D
- **SweepSolid** - Creates 3D shapes by sweeping a 2D profile along a path
- **ModelCutter** - Advanced cutting system for splitting models along wire paths

## Models

### Board Game Inserts

- **Grand Austria Hotel** - Player trays, turn order track, celebrities storage *(work in progress)*

### Hydroponics

- **Basket** - Hydroponic basket with cap ([Thingiverse](https://www.thingiverse.com/thing:7266974), [Maker world](https://makerworld.com/en/models/2162074-hydroponic-basket-with-cap-variety-of-options#profileId-2344140)).
- **Connector** - Pipe connector. 
- **Splitter** - Water pump flow control connector ([Thingiverse](https://www.thingiverse.com/thing:7266985), [Maker world](https://makerworld.com/en/models/2084438-water-pump-flow-control-connector#profileId-2252743)).
- **Stand** - Hydroponic setup stand with side piping.
- **Tray** - Germination tray for Ahopegarden hydroponic system ([Thingiverse](https://www.thingiverse.com/thing:7266976), [Maker world](https://makerworld.com/en/models/2095406-germination-tray-for-ahopegarden-hydroponic-system#profileId-2380658)).

### Other

- **Cable Holder** - Wall-mounted holder with split ball cable organizers *(work in progress)*.
- **Cable Storage** - Wall-mounted cable organizer with railings *(work in progress)*.
- **Power Adapters** - Modular power adapter storage system *(work in progress)*.

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
