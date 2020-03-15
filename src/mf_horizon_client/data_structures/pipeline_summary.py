import datetime

from dataclasses import dataclass


@dataclass
class PipelineSummary:
    """ High level information about a pipeline """

    id_: int
    name: str
    blueprint: str  # One of blueprint type
    creation_date: datetime.datetime
    creation_user: int
    dataset_name: str
