import datetime
from typing import Dict, List, Optional, Union

from dataclasses import dataclass

from mf_horizon_client.data_structures.raw_column import RawColumn


@dataclass
class DatasetSummary:
    name: str
    id_: int
    n_rows: int
    n_columns: int
    upload_date: datetime.datetime
    upload_user_id: int
    time_index: str
    description: str = "Description unspecified"
    columns: Union[List[RawColumn], None] = None

    @property
    def column_ids(self) -> List[int]:
        """ List of column ids in same order as `columns` """
        if self.columns:
            return [column.id_ for column in self.columns]
        return []

    @property
    def column_index(self) -> Dict[int, RawColumn]:
        """ Dict of column id to `RawColumn` """
        if self.columns:
            return {column.id_: column for column in self.columns}
        return {}

    def column_names(self, ids: Optional[List[int]] = None) -> List[str]:
        """
        Gets a list of the names of the specified columns in the same order as
        the supplied id list. If `ids` is None, Returns a list of all column names.
        """

        if self.columns is None:
            raise ValueError("Please load individual data set to see columns.")

        if ids is None:
            return [column.name for column in self.columns]
        else:
            columns = self.column_index
            return [columns[id_].name for id_ in ids]
