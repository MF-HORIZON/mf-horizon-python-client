from enum import Enum


class BlueprintType(Enum):
    """
    A blueprint is a pipeline template in horizon, and must be specified when creating a new pipeline


    Nonlinear
    ===============================================================================================================
    A nonlinear pipeline combines nonlinear feature generation and selection with a nonlinear regressor to generate
    forecasts that are at a specific target in the future.

    A number of different regressor types are available here:

        1. Mondrian Forest. An adaptation of the probabilistic Mondrian Forest algorithm - https://arxiv.org/abs/1406.2673
           Provides Bayesian-esque error bounds, and is our recommended nonlinear regressor of choice.
        2. XG Boost
        3. Random Forest.

    The stages of a nonlinear pipeline are as follows:

    A. Forecast Specification
    B. Stationarization
    C. Feature Generation
    D. Feature Filtering
    E. Feature Refinement
    F. Nonlinear Backtesting
    G. Nonlinear Prediction

    Linear
    ===============================================================================================================
    A nonlinear pipeline combines nonlinear feature generation with a nonlinear regressor to generate
    forecasts that are at a specific target in the future.

    The regressor used is a Variational Bayesian Linear Regressor

    The stages of a linear pipeline are as follows:

    A. Forecast Specification
    B. Stationarization
    C. Nonlinear Feature Generation
    D. Feature Filtering
    E. Feature Refinement
    F. Linear Backtesting
    G. Linear Prediction

    Fast Forecasting
    ===============================================================================================================
    The fast forecasting pipeline is intended to be used as a quick assessment of a dataset's predictive performance
    It is identical to the linear pipeline, but does not include Feature Refinement.

    The stages of a linear pipeline are as follows:

    A. Forecast Specification
    B. Stationarization
    C. Nonlinear Feature Generation
    D. Feature Filtering
    E. Linear Backtesting
    F. Linear Prediction

    Feature Selection
    ===============================================================================================================
    The feature selection pipeline assumes that the input data set already encodes information about a signal's
    past, such that a horizontal observation vector may be used in a traditional regression sense to map to a target
    value at a point in the future.


          Feat1 | Feat2 | Feat3 | .... | FeatP
    Obs1  -------------------------------------   t
    Obs2  -------------------------------------   t-1
    Obs3  -------------------------------------   t-2
    ...   .....................................
    ...   .....................................
    ObsN  -------------------------------------   t-N

    Two stages of feature selection are then used in order to maximize predictive performance of the feature set
    on specified future points for a given target


    The stages of a linear pipeline are as follows:

    A. Forecast Specification
    B. Feature Filtering
    E. Feature Refinement

    Feature Discovery
    ===============================================================================================================
    The feature discovery pipeline discovers features to maximize performance for a particular forecast target,
    at a specified point in the future. Unlike the feature selection pipeline, it does not assume that the signal
    set has already encoded historical information about the original data's past.

    The stages of a feature discovery pipeline are as follows:

    A. Forecast Specification
    B. Feature Generation
    C. Feature Filtering
    D. Feature Refinement

    Signal Encoding
    ===============================================================================================================
    One of Horizon's feature generation methods is to encode signals in the frequency domain, extracting historic
    lags that will efficiently represent the information contained within them.

    The signal encoding pipeline allows for this functionality to be isolated, where the output is a feature
    set that has encoded past information about a signal that can be exported from the platform

    The stages of a signal encoding pipeline are as follows:

    A. Forecast Specification
    B. Feature Generation
    C. Feature Filtering

    Stationarization
    ===============================================================================================================
    Stationarize a signal set and specified target using Augmented Dicky Fuller analysis, and a detrending method
    for the specified target.

    The stages of a stationarization pipeline are as follows:

    A. Forecast Specification
    B. Stationarization
    """

    nonlinear = "NONLINEAR"
    linear = "LINEAR"
    fast_forecasting = "FAST_FORECAST"
    feature_selection = "FEATURE_SELECTION"
    feature_discovery = "FEATURE_DISCOVERY"
    signal_encoding = "SIGNAL_ENCODING"
    stationarisation = "STATIONARISATION"
