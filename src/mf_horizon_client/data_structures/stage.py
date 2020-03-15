from dataclasses import dataclass

from mf_horizon_client.data_structures.configs.stage_config import StageConfig
from mf_horizon_client.data_structures.configs.stage_status import StageStatus
from mf_horizon_client.schemas.configs import ConfigMultiplexSchema


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
