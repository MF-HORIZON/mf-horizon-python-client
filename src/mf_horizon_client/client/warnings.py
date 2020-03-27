from enum import Enum


class Warnings(Enum):
    NO_MAX_FIRE_AND_FORGET_WORKERS_SPECIFIED = "No maximum number of concurrent pipelines specified. Defaulting to one."
