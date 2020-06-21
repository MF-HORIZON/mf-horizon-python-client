from typing import List
from tqdm import tqdm

from mf_horizon_client.data_structures.pipeline import Pipeline


def update_single_pipeline_status(pipelines: List[Pipeline], progress_bars: List[tqdm], compute_status: dict) -> None:
    """
        Uploads TQDM progress bars and their description.
        :param compute_status: return dict from api
        :param pipelines:
        :param progress_bars: list of tqdm progress bars
        :return:
        """
    for pipeline, progress_bar in zip(pipelines, progress_bars):
        running_stage = pipeline.running_stage
        pending_stage = pipeline.first_pending_stage
        if running_stage:
            progress_bar.set_postfix(
                {
                    "n_scheduled_tasks": compute_status["num_unfinished_run_tasks_for_user"],
                    "compute_worker_status": f"{compute_status['num_busy_workers']} out of {compute_status['num_workers']} cores in use",
                    "currently_processing": f"{running_stage.type.upper()} ({running_stage.id_})",
                }
            )
            progress_bar.set_description(f" Running Pipeline {pipeline.summary.id_}")
            loc = pipeline.stages.index(pipeline.last_completed_stage) + 1 if pipeline.last_completed_stage else 0
            progress_bar.n = loc

        if not running_stage and pending_stage:
            progress_bar.set_description(f" Queued Pipeline {pipeline.summary.id_}")
            loc = pipeline.stages.index(pipeline.last_completed_stage) + 1 if pipeline.last_completed_stage else 0
            progress_bar.n = loc

        if pipeline.is_complete:
            progress_bar.set_description(f" \u2714 Complete Pipeline {pipeline.summary.id_}")
            progress_bar.set_postfix({})
            progress_bar.n = len(pipeline.stages)


def initialise_progress_bar(pipeline: Pipeline) -> tqdm:
    initial = pipeline.stages.index(pipeline.last_completed_stage) + 1 if pipeline.last_completed_stage else 0
    progress_bar = tqdm(total=len(pipeline.stages), initial=initial,)
    progress_bar.set_description(f"Pipeline {pipeline.summary.id_}")
    return progress_bar
