from typing import List, Dict
import pandas as pd

from dataclasses import dataclass


@dataclass
class PredictColumnQuery:
    name: str
    data: List[float]

    def as_json(self):
        return {
            "name": self.name,
            "data": self.data
        }


@dataclass
class Predictions:
    """ The predictions made by a regressor, includes low and high confidence bounds."""

    mean: pd.Series
    cb_low: pd.Series
    cb_high: pd.Series
    confidence: float  # prob. that truth will lie between cb_low and cb_high
    name: str
    regressor_importances: Dict[str, List[float]]

    @property
    def data(self) -> pd.DataFrame:
        df = pd.DataFrame({
            "mean": self.mean.values,
            "cb_low": self.cb_low.values,
            "cb_high": self.cb_high.values,
        })

        df.index = [self.name]
        return df


@dataclass
class PredictResponse:
    target_original_column_name: str
    predictions: Predictions
