import enum


class StageType(enum.Enum):
    """ A complete list of all stages available to use in a pipeline"""

    feature_generation = "feature_generation"
    filtering = "filtering"
    problem_specification = "problem_specification"
    stationarisation = "stationarisation"
    backtest = "backtest"
    refinement = "refinement"
    prediction = "prediction"
