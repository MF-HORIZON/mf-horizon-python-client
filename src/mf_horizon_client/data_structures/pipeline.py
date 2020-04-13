from typing import List, Union

from dataclasses import dataclass
from mf_horizon_client.data_structures.configs.stage_status import StageStatus
from mf_horizon_client.data_structures.configs.stage_types import StageType
from mf_horizon_client.data_structures.dataset_summary import DatasetSummary
from mf_horizon_client.data_structures.pipeline_summary import PipelineSummary
from mf_horizon_client.data_structures.stage import Stage


@dataclass
class Pipeline:
    """
    A Pipeline consists of a series of stages, which can be run to perform analysis,
    generate features, or make predictions from a dataset.
    """

    summary: PipelineSummary
    stages: List[Stage]
    dataset: DatasetSummary

    def find_stage_by_type(self, stage_type: StageType) -> List[Stage]:
        """
        Returns all stages of a given type in a pipeline

        :param stage_type: Type of stage (see stage type)
        :return: List of stages of a given type in a pipeline
        """
        stages = self.stages

        return [stage for stage in stages if stage.type == stage_type.value]

    @property
    def is_running(self) -> bool:
        return any(stage.status == StageStatus.RUNNING.name for stage in self.stages)

    @property
    def is_complete(self) -> bool:
        return all(stage.status == StageStatus.COMPLETE.name for stage in self.stages)

    @property
    def is_errored(self) -> bool:
        return any(stage.status == StageStatus.ERROR.name for stage in self.stages)

    @property
    def is_pending(self) -> bool:
        return any(stage.status == StageStatus.PENDING.name for stage in self.stages)

    @property
    def running_stage(self) -> Union[Stage, None]:
        """
        If a stage is running in the pipeline, return this stage
        """
        stages = [stage for stage in self.stages if stage.status == StageStatus.RUNNING.name]
        if len(stages) == 1:
            return stages[0]
        return None

    @property
    def first_pending_stage(self) -> Union[Stage, None]:
        """
        If stages are pending in the pipeline, return the first pending stage
        """
        stages = [stage for stage in self.stages if stage.status == StageStatus.PENDING.name]
        if len(stages) <= 0:
            return None
        return stages[0]

    @property
    def last_completed_stage(self) -> Union[Stage, None]:
        """
        If stages are complete in the pipeline, return the last complete stage
        """
        stages = [stage for stage in self.stages if stage.status == StageStatus.COMPLETE.name]
        if len(stages) <= 0:
            return None
        return stages[-1]
