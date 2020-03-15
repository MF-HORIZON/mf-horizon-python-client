import enum


class StageStatus(enum.Enum):
    """
    Defines the current state of a stage, controlling whether it can be run etc.
    Ready -     stage is available to be run as part of a pipeline.
    Running -   stage is currently running
    Complete -  stage has finished running and results have been saved
    Pending -   stage is part of a pipeline which is currently running, and will be run
                when prerequisite stages are completed. Status will then be set to
                complete
    Error -     An error was found when running the stage. Results may be incomplete or
                nonexistent.
    """

    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    PENDING = "PENDING"
    ERROR = "ERROR"
