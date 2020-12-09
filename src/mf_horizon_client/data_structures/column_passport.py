from typing import Any, List

from dataclasses import dataclass
import pandas as pd


@dataclass
class ColumnPassport:
    """
    Summary statistics of a raw column.
    """

    id_: int
    name: str
    cadence: pd.Timedelta
    autocorrelations: Any
    minimum: float
    maximum: float
    n_rows: int
    is_text: bool
    is_binary: bool
    adf: float
    quality: float
    intraday_available: bool
    binary_labels: List[str]

    def __post_init__(self) -> None:
        self.name = str(self.name)
        self.cadence = pd.to_timedelta(self.cadence)
        self.id_ = int(self.id_)
        self.minimum = float(self.minimum)
        self.maximum = float(self.maximum)
        self.n_rows = int(self.n_rows)
        self.adf = float(self.adf)
        self.quality = float(self.quality)
