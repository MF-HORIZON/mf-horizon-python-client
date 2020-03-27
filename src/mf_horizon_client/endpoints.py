from urllib.parse import urljoin

# pylint: disable=C0103

BASE_URL = "api/"


def validate_url(url: str):
    """
    validates that a url is likely to be of the right format
    """

    assert url[0] != "/", "Endpoint Error - please remove the leading slash from endpoint url"


def create_full_static_endpoint(endpoint: str):
    validate_url(urljoin(BASE_URL, endpoint))
    return urljoin(BASE_URL, endpoint)


# noinspection PyPep8Naming
class Endpoints:
    """
    Builds all endpoints for the Horizon API
    """

    HEALTH = create_full_static_endpoint("healthz/")
    STATUS = create_full_static_endpoint("pipelines/workers/status")
    UPLOAD_DATA = create_full_static_endpoint("datasets/upload")
    ALL_DATASETS = create_full_static_endpoint("datasets/")
    PIPELINES = create_full_static_endpoint("pipelines/")

    @staticmethod
    def SINGLE_DATASET(dataset_id: int):
        return f"{Endpoints.ALL_DATASETS}{dataset_id}"

    @staticmethod
    def SINGLE_SERIES(dataset_id: int, series_id: int):
        return f"{Endpoints.SINGLE_DATASET(dataset_id)}/{series_id}/plot"

    @staticmethod
    def SINGLE_SERIES_CORRELATIONS_WITH_OTHER_SERIES(dataset_id: int, series_id: int):
        return f"{Endpoints.SINGLE_DATASET(dataset_id)}/{series_id}/correlation"

    @staticmethod
    def SINGLE_SERIES_MUTUAL_INFORMATION_WITH_OTHER_SERIES(dataset_id: int, series_id: int):
        return f"{Endpoints.SINGLE_DATASET(dataset_id)}/{series_id}/mutual_info"

    @staticmethod
    def SINGLE_SERIES_AUTOCORRELATION(dataset_id: int, series_id: int):
        return f"{Endpoints.SINGLE_DATASET(dataset_id)}/{series_id}/autocorrelation"

    @staticmethod
    def RENAME_DATASET(dataset_id: int):
        return f"{Endpoints.SINGLE_DATASET(dataset_id)}/name"

    @staticmethod
    def SINGLE_PIPELINE(pipeline_id: int):
        return f"{Endpoints.PIPELINES}{pipeline_id}"

    @staticmethod
    def STAGES(pipeline_id: int):
        return f"{Endpoints.PIPELINES}/{pipeline_id}/stages"

    @staticmethod
    def SINGLE_STAGE(pipeline_id: int, stage_id: int):
        return f"{Endpoints.STAGES(pipeline_id)}/{stage_id}"

    @staticmethod
    def UPDATE_STAGE_CONFIGURATION(pipeline_id: int, stage_id: int):
        return f"{Endpoints.SINGLE_STAGE(pipeline_id, stage_id)}/config"

    @staticmethod
    def RUN_PIPELINE(pipeline_id: int):
        return f"{Endpoints.PIPELINES}/{pipeline_id}/run"

    @staticmethod
    def INSIGHTS_FOR_STAGE(pipeline_id: int, stage_id: int):
        return f"{Endpoints.SINGLE_STAGE(pipeline_id, stage_id)}/insights"

    @staticmethod
    def FEATURES_FOR_STAGE(pipeline_id: int, stage_id: int):
        return f"{Endpoints.SINGLE_STAGE(pipeline_id, stage_id)}/features"

    @staticmethod
    def FEATURE_DATA_FOR_STAGE(pipeline_id: int, stage_id: int, horizon: int):
        return f"{Endpoints.SINGLE_STAGE(pipeline_id, stage_id)}/feature_data?horizon={horizon}"

    @staticmethod
    def BACKTEST_DATA_FOR_STAGE(pipeline_id: int, stage_id: int, horizon: int):
        return f"{Endpoints.SINGLE_STAGE(pipeline_id, stage_id)}/backtest_data?horizon={horizon}"

    @staticmethod
    def EXPERT_BACKTEST_FOR_STAGE_AND_HORIZON(
        pipeline_id: int, horizon: int, first_row: int, last_row: int, n_training_rows: int, stage_id: int,
    ):
        return (
            f"{Endpoints.SINGLE_PIPELINE(pipeline_id)}/expert/backtest?first={first_row}"
            f"&last={last_row}&train={n_training_rows}&stage={stage_id}&horizon={horizon} "
        )
