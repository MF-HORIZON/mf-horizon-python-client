import enum

from dataclasses import dataclass
from mf_horizon_client.data_structures.configs.stage_config import StageConfig
from mf_horizon_client.data_structures.configs.stage_status import StageStatus
from mf_horizon_client.schemas.configs import ConfigMultiplexSchema


class StageRunMode(enum.Enum):
    """
    Defines the current run mode of the stage.
    Full -  The stage will run normally
    Preview - The stage will run in a quick preview mode
    """

    FULL = "full"
    PREVIEW = "preview"


@dataclass
class Stage:
    """
    Python client representation of a Horizon Stage
    """

    def __post_init__(self):
        # noinspection PyTypeChecker
        self.config = ConfigMultiplexSchema().load(self.config)

    status: StageStatus
    id_: int
    type: str  # One of StageType.values
    config: StageConfig
    run_mode: StageRunMode
    n_true_target_rows_for_plot: int = 500
