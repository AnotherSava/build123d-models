# Type stub for build123d package
# Provides enhanced type information for property-based constants

from typing import ClassVar

# Only define the classes where we need to override type information
# Everything else will fall through to the actual build123d package

class Plane:
    """Stub for Plane class with property constants typed correctly"""
    XY: ClassVar[Plane]
    XZ: ClassVar[Plane]
    YX: ClassVar[Plane]
    YZ: ClassVar[Plane]
    ZX: ClassVar[Plane]
    ZY: ClassVar[Plane]
    def __init__(self, *args, **kwargs) -> None: ...

class Axis:
    """Stub for Axis class with property constants typed correctly"""
    X: ClassVar[Axis]
    Y: ClassVar[Axis]
    Z: ClassVar[Axis]
    def __init__(self, *args, **kwargs) -> None: ...
