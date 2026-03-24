"""Module defining the core Appliance data structure."""
from dataclasses import dataclass

@dataclass
class Appliance:
    """Represents a shiftable household appliance for load scheduling."""
    name: str
    power_kw: float
    duration_h: float
    window_start: int = 0   # Default to 00:00 if not specified
    window_end: int = 23    # Default to 23:00 if not specified

    def __post_init__(self) -> None:
        """Validates appliance parameters immediately upon initialization."""
        if self.power_kw <= 0:
            raise ValueError(f"Appliance '{self.name}' must have power_kw > 0.")
        if self.duration_h <= 0:
            raise ValueError(f"Appliance '{self.name}' must have duration_h > 0.")
        if self.window_start < 0 or self.window_end > 23 or self.window_start > self.window_end:
            raise ValueError(f"Invalid time window for {self.name}: {self.window_start}-{self.window_end}")