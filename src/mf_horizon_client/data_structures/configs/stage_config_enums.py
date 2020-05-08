from enum import Enum


class CorrelationMethod(Enum):
    mutual_info = "mutual_info"
    spearman = "spearman"
    pearson = "pearson"
    kendall = "kendall"


class StationarisationStrategy(Enum):
    keep_fail = "keep_fail"
    discard_fail = "discard_fail"
    none = "none"


class TargetTransformType(Enum):
    DoNothing = "DoNothingTargetTransform"
    HorizonLagDiff = "HorizonDiff"
    HorizonLagDiffRatio = "HorizonDiffRatio"


class FeatureGeneratorType(Enum):
    autolag = "autolag"
    ewma = "ewma"
    logarithm = "logarithm"
    lag = "lag"
    num_peaks = "num_peaks"
    rolling_average = "rolling_average"
    perc_change = "perc_change"


class RegressorType(Enum):
    RandomForest = "RandomForest"
    Martingale = "Martingale"
    VBLinReg = "VBLinReg"
    MondrianForest = "MondrianForest"
    XGBoost = "XGBoost"
