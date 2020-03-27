import abc
import json
from typing import List

from mf_horizon_client.data_structures.configs.stage_config_enums import (
    CorrelationMethod,
    FeatureGeneratorType,
    RegressorType,
    StationarisationStrategy,
    TargetTransformType,
)
from mf_horizon_client.data_structures.configs.stage_types import StageType
from mf_horizon_client.data_structures.feature_id import FeatureId


class StageConfig(abc.ABC):
    """ Properties for a stage """

    @abc.abstractmethod
    def as_json(self) -> str:
        """ Returns serialized version of config """

    @classmethod
    @abc.abstractmethod
    def from_json(cls, json_config: str) -> "StageConfig":
        """ Loads a stage config from its serialized counterpart """

    @classmethod
    @abc.abstractmethod
    def get_default(cls) -> "StageConfig":
        """ Return a stage configuration with default parameters """

    @property
    @abc.abstractmethod
    def valid_configuration_values(self):
        """ Validate the  numeric configurations"""


class FilterStageConfig(StageConfig):
    def __init__(self, max_n_features: int, method: CorrelationMethod):
        self.max_n_features = max_n_features
        self.method = method

    def as_json(self) -> str:
        return json.dumps({"max_n_features": self.max_n_features, "method": self.method.name, "type": StageType.filtering.value,})

    @classmethod
    def from_json(cls, json_config: str) -> "FilterStageConfig":
        config = json.loads(json_config)

        return cls(max_n_features=config["max_n_features"], method=CorrelationMethod(config["method"]),)

    @classmethod
    def get_default(cls) -> "FilterStageConfig":
        return FilterStageConfig(max_n_features=30, method=CorrelationMethod.pearson)

    @property
    def valid_configuration_values(self) -> bool:
        """Checks if the numeric values are permitted"""
        if self.max_n_features < 5:
            return False
        if self.max_n_features > 50:
            return False
        return True


class RefinementStageConfig(StageConfig):
    def __init__(
        self, min_features: int, max_features: int, early_stopping_sensitivity: float, deep_search: bool, regressor: RegressorType,
    ):
        """
        :param min_features: - how far to reduce the feature set before stopping,
            irrespective of whether still improving
        :param max_features: - max size of feature set after which to try early stopping
        :param early_stopping_sensitivity: - float between 0-1 which defines how
            sensitive to early stopping. value of 1 means will stop as soon as no
            improvement witnessed, given max_features already passed.
        :param deep_search: - whether to try dropping each feature at every iteration,
            or only a subset (50%)
        :param regressor: - which regressor to use at all refinement iterations
        """
        self.min_features = min_features
        self.max_features = max_features
        self.early_stopping_sensitivity = early_stopping_sensitivity
        self.deep_search = deep_search
        self.regressor = regressor

        assert self.max_features >= self.min_features, "Max features must be < min in RFE"
        assert 0 <= self.early_stopping_sensitivity <= 1, "Early stopping sensitivity must be between 0 and 1 in RFE"
        assert self.min_features >= 1, "Must retain at least one feature in RFE"

    def as_json(self) -> str:
        return json.dumps(
            {
                "min_features": self.min_features,
                "max_features": self.max_features,
                "early_stopping_sensitivity": self.early_stopping_sensitivity,
                "deep_search": self.deep_search,
                "regressor": self.regressor.name,
                "type": StageType.refinement.value,
            }
        )

    @classmethod
    def from_json(cls, json_config: str) -> "RefinementStageConfig":
        config = json.loads(json_config)
        return cls(
            min_features=config["min_features"],
            max_features=config["max_features"],
            early_stopping_sensitivity=config["early_stopping_sensitivity"],
            deep_search=config["deep_search"],
            regressor=RegressorType[config["regressor"]],
        )

    @classmethod
    def get_default(cls) -> "RefinementStageConfig":
        return RefinementStageConfig(
            min_features=5, max_features=20, early_stopping_sensitivity=0, deep_search=False, regressor=RegressorType.RandomForest,
        )

    @property
    def early_stopping_iters(self) -> int:
        """
        y intercept = 2 since at least 2 iterations are required to assess if an
        improvement has been witnessed.

        Gradient of 10 gives a maximum of 12 iterations with no improvement allowed
        before early stopping kicks in, and also simplifies the mapping from sensitivity
        to early stopping iterations.
        """
        iterations = int(12 - 10 * self.early_stopping_sensitivity)
        assert iterations >= 2, "iterations to assess early stopping must be at least 2"
        return iterations

    @property
    def valid_configuration_values(self) -> bool:
        """Checks if the numeric values are permitted"""

        if self.early_stopping_sensitivity > 1:
            return False
        if self.early_stopping_sensitivity < 0:
            return False
        if self.max_features > 50:
            return False
        if self.max_features < self.min_features:
            return False
        if self.min_features < 1:
            return False
        if self.min_features > 50:
            return False
        return True


class StationarisationStageConfig(StageConfig):
    def __init__(
        self, adf_threshold: float, strategy: StationarisationStrategy, target_transform: TargetTransformType,
    ):
        self.adf_threshold = adf_threshold
        self.strategy = strategy
        self.target_transform = target_transform

    def as_json(self) -> str:
        return json.dumps(
            {
                "adf_threshold": self.adf_threshold,
                "strategy": self.strategy.name,
                "target_transform": self.target_transform.name,
                "type": StageType.stationarisation.value,
            }
        )

    @classmethod
    def from_json(cls, json_config: str) -> "StationarisationStageConfig":
        config = json.loads(json_config)

        return cls(
            adf_threshold=config["adf_threshold"],
            strategy=StationarisationStrategy[config["strategy"]],
            target_transform=TargetTransformType[config["target_transform"]],
        )

    @classmethod
    def get_default(cls) -> "StationarisationStageConfig":
        return StationarisationStageConfig(
            adf_threshold=0.03, strategy=StationarisationStrategy.keep_fail, target_transform=TargetTransformType.DoNothing,
        )

    @property
    def valid_configuration_values(self) -> bool:
        """Checks if the numeric values are permitted"""
        if self.adf_threshold < 0.001:
            return False
        if self.adf_threshold > 1:
            return False
        return True


class ProblemSpecificationConfig(StageConfig):
    def __init__(
        self, target_feature: FeatureId, horizons: List[int], data_split: float, active_columns: List[int],
    ):
        self.target_feature = target_feature
        self.horizons = horizons
        self.data_split = data_split
        self.active_columns = active_columns

    def as_json(self) -> str:
        return json.dumps(
            {
                "target_feature": str(self.target_feature),
                "horizons": self.horizons,
                "data_split": self.data_split,
                "active_columns": self.active_columns,
                "type": StageType.problem_specification.value,
            }
        )

    @classmethod
    def get_default(cls) -> "ProblemSpecificationConfig":
        return ProblemSpecificationConfig(
            target_feature=FeatureId("unspecified"), horizons=[1, 2, 3, 4, 5], data_split=0.75, active_columns=[],
        )

    @classmethod
    def from_json(cls, json_config: str) -> "ProblemSpecificationConfig":
        return cls(**json.loads(json_config))

    @property
    def valid_configuration_values(self) -> bool:
        """Checks if the numeric values are permitted"""
        if len(self.horizons) > 40:
            return False
        if any(horizon < 1 for horizon in self.horizons):
            return False
        if self.data_split < 0.1:
            return False
        if self.data_split > 0.9:
            return False
        return True


class FeatureGenerationStageConfig(StageConfig):
    def __init__(self, max_n_features: int, feature_generators: List[FeatureGeneratorType]):
        self.max_n_features = max_n_features
        self.feature_generators = feature_generators

    @classmethod
    def get_default(cls) -> "FeatureGenerationStageConfig":
        return FeatureGenerationStageConfig(
            max_n_features=5000,
            feature_generators=[
                FeatureGeneratorType.autolag,
                FeatureGeneratorType.ewma,
                FeatureGeneratorType.lag,
                FeatureGeneratorType.logarithm,
                FeatureGeneratorType.rolling_average,
            ],
        )

    def as_json(self) -> str:
        return json.dumps(
            {
                "max_n_features": self.max_n_features,
                "feature_generators": [g.name for g in self.feature_generators],
                "type": StageType.feature_generation.value,
            }
        )

    @classmethod
    def from_json(cls, json_config: str) -> "FeatureGenerationStageConfig":
        kwargs = json.loads(json_config)
        kwargs["feature_generators"] = [FeatureGeneratorType[name] for name in kwargs["feature_generators"]]
        return cls(**kwargs)

    @property
    def valid_configuration_values(self) -> bool:
        """Checks if the numeric values are permitted"""

        if self.max_n_features > 10000:
            return False
        if self.max_n_features < 50:
            return False
        return True


class BacktestStageConfig(StageConfig):
    def __init__(
        self, n_backtests: int, fold_train_frac: float, gapping_factor: float, regressor: RegressorType,
    ):
        self.n_backtests = n_backtests
        self.fold_train_frac = fold_train_frac
        self.gapping_factor = gapping_factor
        self.regressor = regressor

    @classmethod
    def get_default(cls) -> "BacktestStageConfig":
        return BacktestStageConfig(n_backtests=3, fold_train_frac=0.4, gapping_factor=0.0, regressor=RegressorType.VBLinReg,)

    def as_json(self) -> str:
        return json.dumps(
            {
                "n_backtests": self.n_backtests,
                "fold_train_frac": self.fold_train_frac,
                "gapping_factor": self.gapping_factor,
                "regressor": self.regressor.name,
                "type": StageType.backtest.value,
            }
        )

    @classmethod
    def from_json(cls, json_config: str) -> "BacktestStageConfig":
        config_dict = json.loads(json_config)
        config_dict["regressor"] = RegressorType[config_dict["regressor"]]

        return cls(**config_dict)

    @property
    def valid_configuration_values(self) -> bool:
        """Checks if the numeric values are permitted"""

        if self.n_backtests > 20:
            return False
        if self.n_backtests < 1:
            return False
        if self.gapping_factor < 0:
            return False
        if self.gapping_factor > 0.5:
            return False
        if self.fold_train_frac < 0.1:
            return False
        if self.fold_train_frac > 0.9:
            return False
        return True


class PredictionStageConfig(StageConfig):
    def __init__(self, regressor: RegressorType):
        self.regressor = regressor

    @classmethod
    def get_default(cls) -> "PredictionStageConfig":
        return PredictionStageConfig(regressor=RegressorType.VBLinReg)

    def as_json(self) -> str:
        return json.dumps({"regressor": self.regressor.name, "type": StageType.prediction.value})

    @classmethod
    def from_json(cls, json_config: str) -> "PredictionStageConfig":
        config_dict = json.loads(json_config)
        config_dict["regressor"] = RegressorType[config_dict["regressor"]]
        return cls(**config_dict)

    @property
    def valid_configuration_values(self) -> bool:
        return True
