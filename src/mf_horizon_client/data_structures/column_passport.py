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
    n_rows: int
    is_text: bool
    is_binary: bool
    intraday_available: bool
    binary_labels: List[str]

    def __post_init__(self) -> None:
        self.name = str(self.name)
        self.cadence = pd.to_timedelta(self.cadence)
        self.id_ = int(self.id_)
        self.n_rows = int(self.n_rows)
