import datetime
from enum import Enum
from typing import Optional

from dataclasses import dataclass


class IngestionStatus(Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    error = "error"


@dataclass
class IngestionProcess:
    dataset_name: str
    id_: int
    upload_size_bytes: int
    creation_date: datetime.datetime
    creation_user_id: int
    status: IngestionStatus
    error: Optional[str]
    task_id: Optional[str]
    dataset_id: Optional[int]
    last_update_error: Optional[str]
    last_update_date: Optional[datetime.datetime]
