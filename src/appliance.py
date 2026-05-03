"""Module defining the core Appliance data structure."""
from dataclasses import dataclass

@dataclass
class Appliance:
    """Represents a shiftable household appliance for load scheduling.

    Time-window convention:
      window_start = earliest hour the appliance may START (inclusive)
      window_end   = latest hour by which the appliance must FINISH (inclusive)

    A cycle of `duration_h` hours starting at hour `s` occupies slots
    [s, s+1, ..., s+ceil(duration_h)-1] and finishes at hour
    s + ceil(duration_h). The constraint enforced everywhere downstream is:

        window_start <= s   AND   s + ceil(duration_h) <= window_end

    The default window 0..24 means "any time of day". window_end may go up
    to 24 (= midnight / end of day).
    """
    name: str
    power_kw: float
    duration_h: float
    window_start: int = 0
    window_end: int = 24

    def __post_init__(self) -> None:
        """Validates appliance parameters immediately upon initialization."""
        if self.power_kw <= 0:
            raise ValueError(f"Appliance '{self.name}' must have power_kw > 0.")
        if self.duration_h <= 0:
            raise ValueError(f"Appliance '{self.name}' must have duration_h > 0.")
        if self.window_start < 0 or self.window_end > 24 or self.window_start >= self.window_end:
            raise ValueError(
                f"Invalid time window for {self.name}: "
                f"{self.window_start}:00-{self.window_end}:00 (must satisfy "
                f"0 <= window_start < window_end <= 24)."
            )