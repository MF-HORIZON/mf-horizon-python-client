import pandas as pd
import numpy as np
from sklearn.metrics import classification_report


def binary_backtests_returns(backtests: pd.DataFrame,) -> pd.DataFrame:
    """
    Converts a Horizon backtest data frame into a binary backtests of directions
    """
    return backtests.diff().apply(np.sign).dropna()


def calculate_metrics(y_pred: pd.Series, y_true: pd.Series):
    """
    Takes a Horizon binary backtest data frame and calculate metrics.
    """
    return classification_report(y_true=y_true, y_pred=y_pred, output_dict=True,)


def recommender(last_observed_values: pd.Series, predictions: pd.DataFrame) -> pd.DataFrame:
    means = predictions["mean"]
    spreads = predictions["bound_high"] - predictions["bound_low"]
    spreads.index = predictions["Series"]
    means.index = predictions["Series"]
    changes = means - last_observed_values
    directions = np.sign(changes)
    uncertainties = 100 * spreads / means
    predicted_movement = 100 * changes / last_observed_values[0]
    recommendations = pd.DataFrame(
        [directions, uncertainties, predicted_movement],
        index=["Recommendations", "Predictive Uncertainty Percent", "Predicted Movement Percent"],
    )
    return recommendations
