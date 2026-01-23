from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class ConnectorDimensions:
    length: float
    width: float


class ConnectorType(Enum):
    TYPE_E_ANGLED = ConnectorDimensions(48.0, 36.2)
    TYPE_C = ConnectorDimensions(13.9, 35.4)
    NEMA_1_15P = ConnectorDimensions(19.2, 27) # Type A male
    NEMA_5_15P = ConnectorDimensions(23.2, 24.5) # Type A grounded male
    EIC_C13 = ConnectorDimensions(15.3, 27.3) # PSU female
    EIC_C14 = ConnectorDimensions(16.3, 26.5) # PSU male
    EIC_C7 = ConnectorDimensions(11.9, 16) # Barrel
    EIC_C5 = ConnectorDimensions(16.9, 22.4) # Cloverleaf
    DVI = ConnectorDimensions(15.0, 40.5)
    HDMI = ConnectorDimensions(11.2, 20.9)

class CableStorageDimensions:
    pass

class CableStorage:
    def __init__(self, dim: CableStorageDimensions):
        self.dim = dim
