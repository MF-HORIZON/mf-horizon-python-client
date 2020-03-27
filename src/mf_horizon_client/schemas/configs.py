from typing import Any, Dict, Type

from marshmallow import fields, post_load
from marshmallow_enum import EnumField
from marshmallow_oneofschema import OneOfSchema

from mf_horizon_client.data_structures.configs.stage_config import (
    BacktestStageConfig,
    FeatureGenerationStageConfig,
    FilterStageConfig,
    PredictionStageConfig,
    ProblemSpecificationConfig,
    RefinementStageConfig,
    StationarisationStageConfig,
)
from mf_horizon_client.data_structures.configs.stage_config_enums import (
    CorrelationMethod,
    FeatureGeneratorType,
    RegressorType,
    StationarisationStrategy,
    TargetTransformType,
)
from mf_horizon_client.data_structures.configs.stage_types import StageType
from mf_horizon_client.schemas.schema import CamelCaseSchema
from mf_horizon_client.utils.string_case_converters import force_camel_case


class FilteringConfigSchema(CamelCaseSchema):
    method = EnumField(CorrelationMethod, required=True)
    max_n_features = fields.Integer(required=True)

    @post_load  # type: ignore
    def make(  # pylint: disable=no-self-use
        self, data: Any, many: bool, partial: bool,  # pylint: disable=unused-argument  # pylint: disable=unused-argument
    ) -> FilterStageConfig:
        """
        Marshmallow function, invoked after validating and loading json data. Converts
        dictionary loaded from json into a filter stage config object.
        """
        return FilterStageConfig(**data)


class StationarisationConfigSchema(CamelCaseSchema):
    adf_threshold = fields.Float(required=True)
    strategy = EnumField(StationarisationStrategy, required=True)
    target_transform = EnumField(TargetTransformType, required=True)

    @post_load  # type: ignore
    def make(  # pylint: disable=no-self-use
        self, data: Any, many: bool, partial: bool,  # pylint: disable=unused-argument  # pylint: disable=unused-argument
    ) -> StationarisationStageConfig:
        """
        Marshmallow function, invoked after validating and loading json data. Converts
        dictionary loaded from json into a stationarisation stage config object.
        """
        return StationarisationStageConfig(**data)


class ProblemSpecConfigSchema(CamelCaseSchema):
    target_feature = fields.String(required=True)
    horizons = fields.List(fields.Integer(required=True))
    data_split = fields.Float(required=True)
    active_columns = fields.List(fields.Integer(required=False))

    @post_load  # type: ignore
    def make(  # pylint: disable=no-self-use
        self, data: Any, many: bool, partial: bool,  # pylint: disable=unused-argument  # pylint: disable=unused-argument
    ) -> ProblemSpecificationConfig:
        """
        Marshmallow function, invoked after validating and loading json data. Converts
        dictionary loaded from json into a problem specification stage config object.
        """
        return ProblemSpecificationConfig(**data)


class BacktestConfigSchema(CamelCaseSchema):
    n_backtests = fields.Integer(required=True)
    fold_train_frac = fields.Float(required=True)
    gapping_factor = fields.Float(required=True)
    regressor = EnumField(RegressorType, required=True)

    @post_load  # type: ignore
    def make(  # pylint: disable=no-self-use
        self, data: Any, many: bool, partial: bool,  # pylint: disable=unused-argument  # pylint: disable=unused-argument
    ) -> BacktestStageConfig:
        """
        Marshmallow function, invoked after validating and loading json data. Converts
        dictionary loaded from json into a backtest stage config object.
        """
        return BacktestStageConfig(**data)


class RefinementConfigSchema(CamelCaseSchema):
    min_features = fields.Integer(required=True)
    max_features = fields.Integer(required=True)
    early_stopping_sensitivity = fields.Float(required=True)
    deep_search = fields.Boolean(required=True)
    regressor = EnumField(RegressorType, required=True)

    @post_load  # type: ignore
    def make(  # pylint: disable=no-self-use
        self, data: Any, many: bool, partial: bool,  # pylint: disable=unused-argument  # pylint: disable=unused-argument
    ) -> RefinementStageConfig:
        """
        Marshmallow function, invoked after validating and loading json data. Converts
        dictionary loaded from json into a refinement stage config object.
        """
        return RefinementStageConfig(**data)


class FeatureGenerationConfigSchema(CamelCaseSchema):
    max_n_features = fields.Integer(required=True)
    feature_generators = fields.List(EnumField(FeatureGeneratorType, required=True))

    @post_load  # type: ignore
    def make(  # pylint: disable=no-self-use
        self, data: Any, many: bool, partial: bool,  # pylint: disable=unused-argument  # pylint: disable=unused-argument
    ) -> FeatureGenerationStageConfig:
        """
        Marshmallow function, invoked after validating and loading json data. Converts
        dictionary loaded from json into a feature generation stage config object.
        """
        return FeatureGenerationStageConfig(**data)


class PredictionConfigSchema(CamelCaseSchema):
    regressor = EnumField(RegressorType, required=True)

    @post_load  # type: ignore
    def make(  # pylint: disable=no-self-use
        self, data: Any, many: bool, partial: bool,  # pylint: disable=unused-argument  # pylint: disable=unused-argument
    ) -> PredictionStageConfig:
        """
        Marshmallow function, invoked after validating and loading json data. Converts
        dictionary loaded from json into a prediction stage config object.
        """
        return PredictionStageConfig(**data)

    @property
    def valid_configuration_values(self) -> bool:
        return True


class ConfigMultiplexSchema(OneOfSchema):  # type: ignore
    type_schemas = {
        StageType.filtering.name: FilteringConfigSchema,
        StageType.problem_specification.name: ProblemSpecConfigSchema,
        StageType.stationarisation.name: StationarisationConfigSchema,
        StageType.feature_generation.name: FeatureGenerationConfigSchema,
        StageType.backtest.name: BacktestConfigSchema,
        StageType.refinement.name: RefinementConfigSchema,
        StageType.prediction.name: PredictionConfigSchema,
    }

    config_lookup: Dict[Type[Any], str] = {
        FilterStageConfig: StageType.filtering.name,
        ProblemSpecificationConfig: StageType.problem_specification.name,
        StationarisationStageConfig: StageType.stationarisation.name,
        FeatureGenerationStageConfig: StageType.feature_generation.name,
        BacktestStageConfig: StageType.backtest.name,
        RefinementStageConfig: StageType.refinement.name,
        PredictionStageConfig: StageType.prediction.name,
    }

    def get_obj_type(self, obj: Type[Any]) -> str:
        try:
            return self.config_lookup[type(obj)]
        except KeyError:
            raise TypeError(f"Unrecognised type {type(obj)} for multiplex schema, " f"{self.__class__}")

    def on_bind_field(self, field_name, field_obj):
        field_obj.data_key = force_camel_case(field_obj.data_key or field_name)
