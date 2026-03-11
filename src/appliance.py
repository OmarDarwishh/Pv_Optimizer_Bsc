"""Module defining the core Appliance data structure."""
from dataclasses import dataclass

@dataclass
class Appliance:
    """
    Represents a shiftable household appliance for load scheduling.

    Attributes:
        name (str): Identifier for the appliance (e.g., 'Dishwasher').
        power_kw (float): The constant power draw of the appliance in kilowatts.
        duration_h (float): The required operational duration in hours.
    """
    name: str
    power_kw: float
    duration_h: float

    def __post_init__(self) -> None:
        """Validates appliance parameters immediately upon initialization."""
        if self.power_kw <= 0:
            raise ValueError(f"Appliance '{self.name}' must have power_kw > 0.")
        if self.duration_h <= 0:
            raise ValueError(f"Appliance '{self.name}' must have duration_h > 0.")