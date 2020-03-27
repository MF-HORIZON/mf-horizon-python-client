from mf_horizon_client.data_structures.dataset_summary import DatasetSummary
from mf_horizon_client.data_structures.pipeline import Pipeline
from mf_horizon_client.data_structures.pipeline_summary import PipelineSummary
from mf_horizon_client.data_structures.stage import Stage
from mf_horizon_client.utils.string_case_converters import convert_dict_from_camel_to_snake


def construct_pipeline_class(pipeline) -> Pipeline:
    stages = [Stage(**convert_dict_from_camel_to_snake(stage)) for stage in pipeline["stages"]]
    return Pipeline(
        summary=PipelineSummary(**convert_dict_from_camel_to_snake(pipeline["summary"])),
        stages=stages,
        dataset=DatasetSummary(**convert_dict_from_camel_to_snake(pipeline["dataset"])),
    )
