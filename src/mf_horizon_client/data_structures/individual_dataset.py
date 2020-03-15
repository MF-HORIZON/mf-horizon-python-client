from typing import List

from dataclasses import dataclass

from mf_horizon_client.data_structures.column_passport import ColumnPassport
from mf_horizon_client.data_structures.dataset_summary import DatasetSummary


@dataclass
class IndividualDataset:

    analysis: List[ColumnPassport]
    summary: DatasetSummary
