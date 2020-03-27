import json
from io import StringIO
from time import sleep
from typing import Any, Dict, List, cast

import numpy as np
import pandas as pd
from tqdm import tqdm

from mf_horizon_client.client.datasets.data_interface import DataInterface
from mf_horizon_client.client.pipelines.blueprints import BlueprintType
from mf_horizon_client.client.pipelines.construct_pipeline_class import construct_pipeline_class
from mf_horizon_client.data_structures.configs.stage_config import ProblemSpecificationConfig, StageConfig, StationarisationStageConfig
from mf_horizon_client.data_structures.configs.stage_config_enums import StationarisationStrategy
from mf_horizon_client.data_structures.configs.stage_types import StageType
from mf_horizon_client.data_structures.pipeline import Pipeline
from mf_horizon_client.data_structures.stage import Stage
from mf_horizon_client.endpoints import Endpoints
from mf_horizon_client.utils import terminal_messages
from mf_horizon_client.utils.catch_method_exception import catch_errors
from mf_horizon_client.utils.progress_bar_helpers import (
    initialise_progress_bar,
    update_single_pipeline_status,
)
from mf_horizon_client.utils.string_case_converters import (
    convert_dict_from_camel_to_snake,
    convert_dict_from_snake_to_camel,
)


class PipelineInterface:
    def __init__(self, client):
        """
        :param client: HorizonClient
        """
        self.client = client

    @catch_errors
    def create_pipeline(self, dataset_id: int, blueprint: BlueprintType, name: str) -> Pipeline:
        """
        Creates a pipeline, which is a set of stages coupled with a data set. Pipelines are the core
        component in Horizon, and are instantiated via reference to a 'blueprint' - the equivalent of a
        pipeline template.

        Blueprints define the structure of a Horizon pipeline, and a set of appropriate default settings for each stage.
        Although a blueprint defines a stage, it does not enforce a stage configuration. These may be freely modified
        via the user-interface or programmatically.

        Please see 'blueprints.py' for a full explanation of the available blueprint types (BlueprintType)

        :param dataset_id: Unique identifier of a dataset.
        :param blueprint: Desired pipeline blueprint type
        :param name: User-specified pipeline name
        """

        pipeline = self.client.put(Endpoints.PIPELINES, json={"name": name, "datasetId": dataset_id, "blueprint": blueprint.name},)

        return self.get_single_pipeline(construct_pipeline_class(pipeline).summary.id_)

    @catch_errors
    def list_pipelines(self) -> List[Pipeline]:
        """
        Gets a summary of all pipelines currently owned by the current user.
        :return: A list of Pipelines
        """

        pipelines = self.client.get(Endpoints.PIPELINES)
        return [construct_pipeline_class(pipeline) for pipeline in pipelines]

    @catch_errors
    def get_single_pipeline(self, pipeline_id: int) -> Pipeline:
        """
        Gets a summary of all pipelines currently owned by the current user.
        :return: A list of Pipelines
        """

        data_interface = DataInterface(self.client)
        pipeline = self.client.get(Endpoints.SINGLE_PIPELINE(pipeline_id=pipeline_id))
        pipeline = construct_pipeline_class(pipeline)
        dataset = data_interface.get_dataset(pipeline.dataset.id_)
        pipeline.dataset = dataset.summary
        return pipeline

    @catch_errors
    def find_stage_by_type(self, pipeline_id: int, stage_type: StageType) -> List[Stage]:
        """
        Returns all stages of a given type in a pipeline

        :param pipeline_id: ID of a pipeline
        :param stage_type: Type of stage (see StageType)
        :return: List of stages of a given type in a pipeline
        """

        pipeline = self.get_single_pipeline(pipeline_id)
        return [stage for stage in pipeline.stages if stage.type == stage_type]

    @catch_errors
    def update_config(self, pipeline_id: int, stage_id: int, config: StageConfig):
        """
        Updates the configuration of a stage. All dependent insights will be reset.

        :param pipeline_id: ID of a pipeline
        :param stage_id: ID of a stage
        :param config: stage config
        :return:
        """

        pipeline = self.get_single_pipeline(pipeline_id)
        stages_matching_id = [stage for stage in pipeline.stages if stage.id_ == stage_id]

        assert len(stages_matching_id) == 1, "No stage found with given identifier"
        assert config.valid_configuration_values, "Invalid numeric configuration specified"
        config_dict = json.loads(config.as_json())

        self.client.put(
            Endpoints.UPDATE_STAGE_CONFIGURATION(pipeline_id, stage_id), json=convert_dict_from_snake_to_camel(config_dict),
        )

    @catch_errors
    def wait_for_pipeline_completion(self, pipeline_ids: List[int], _progress_bars=None, verbose=True):
        """
        Function that waits until a running pipeline is complete before returning

        :param pipeline_ids:
        :param _progress_bars: List of TQDM progress bars (only used in recursive calls)
        :param verbose: If true then show output
        :return:
        """

        def should_return(pipeline: Pipeline):
            if pipeline.is_complete or pipeline.is_errored:
                if pipeline.is_complete:
                    return True
                if pipeline.is_errored:
                    terminal_messages.print_failure(f"Pipeline {pipeline.summary.id_} ({pipeline.summary.name}) errored!")
                    return True
            return False

        sleep(1)  # Give the api some time to recover from being ambushed
        pipelines = [self.get_single_pipeline(pipeline_id=pipeline_id) for pipeline_id in pipeline_ids]

        if not _progress_bars and verbose:
            _progress_bars = [initialise_progress_bar(pipeline) for pipeline in pipelines]

        if all(should_return(pipeline) for pipeline in pipelines):
            if not verbose:
                return
            for pipeline, progress_bar in zip(pipelines, _progress_bars):
                terminal_messages.print_success(f"Pipeline {pipeline.summary.id_} ({pipeline.summary.name}) successfully completed!")
                progress_bar.clear()
                progress_bar.close()
            return

        if verbose:
            compute_status = convert_dict_from_camel_to_snake(self.client.horizon_compute_status())
            update_single_pipeline_status(pipelines, _progress_bars, compute_status)
            self.wait_for_pipeline_completion(pipeline_ids, _progress_bars=_progress_bars)
        else:
            self.wait_for_pipeline_completion(pipeline_ids, verbose=False)

    @catch_errors
    def run_pipeline(self, pipeline_id: int, synchronous: bool = False, verbose: bool = True,) -> Pipeline:
        """
        Runs a single pipeline with the given ID.

        WARNING: If synchronous=False then please make sure not to overload the number of fire and forget workers.

        :param pipeline_id: Unique pipeline identifier
        :param synchronous: If synchronous, waits for the pipeline to complete before returning.
        :param verbose: If false, suppress output
        :return: Pipeline object (completed if synchronous)
        """
        pipeline = self.get_single_pipeline(pipeline_id)
        if pipeline.is_complete:
            terminal_messages.print_failure(f"Pipeline {pipeline_id} not run - already complete")
        self.client.post(Endpoints.RUN_PIPELINE(pipeline_id))
        if synchronous:
            self.wait_for_pipeline_completion(pipeline_ids=[pipeline_id], verbose=verbose)
        pipeline = self.get_single_pipeline(pipeline_id)

        return pipeline

    def get_insight_for_stage(self, pipeline_id: int, stage_id: int) -> Dict[str, Any]:
        """
        Fetches the high-level output results for a stage. Feature set information is retrieved using get_features_for_stage - the insights
        here are concerned more with the bigger picture.

        :param pipeline_id: ID of a pipeline
        :param stage_id: ID of a stage
        :return: Stage insights in dictionary form
        """

        response = self.client.get(Endpoints.INSIGHTS_FOR_STAGE(pipeline_id=pipeline_id, stage_id=stage_id,))

        return convert_dict_from_camel_to_snake(response)

    def get_feature_info_for_stage(self, pipeline_id: int, stage_id: int) -> pd.DataFrame:
        """
        Returns a list of the features that have passed a given stage, and their associated transforms and metadata.

        :param pipeline_id: ID of a pipeline
        :param stage_id: ID of a stage
        :return: Dataframe containing the feature metadata (with each row being a feature)
        """
        features = []

        def get_children(feature_list: List[Any], current_horizon: str) -> None:
            """
            Depth-first search of feature tree; appending the leaf features into the feature list supplied.
            :param feature_list: List to be modified by this function
            :param current_horizon: current forecast horizon being searched
            :return: None (Function has side effect of modifying feature_list)
            """
            for feature in feature_list:
                if feature["active"]:
                    features.append(
                        {
                            "feature_name": feature["name"],
                            "feature_type": feature["type"],
                            "active": feature["active"],
                            "json_config": json.dumps(feature["config"]),
                            "horizon": current_horizon,
                        }
                    )
                if feature["children"]:
                    get_children(feature["children"], current_horizon)

        response = self.client.get(Endpoints.FEATURES_FOR_STAGE(pipeline_id=pipeline_id, stage_id=stage_id,))
        for horizon in response["horizons"]:
            features_for_horizon = response["horizons"][horizon]["features"]
            get_children(features_for_horizon, horizon)
        df = pd.DataFrame.from_records(features)
        df["active"].astype(bool)
        return df

    @catch_errors
    def download_feature_info_for_stage(self, pipeline_id: int, stage_id: int) -> Dict[str, pd.DataFrame]:
        """
        Downloads the feature data as a data frame.

        WARNING: Total size of data is limited to 100mb * number of horizons (i.e. 2GB if you don't override the
        class checks for maximum number of horizons that can be selected!).

        :param pipeline_id: ID of a pipeline
        :param stage_id: ID of a stage
        :return: Dictionary of Dataframes of feature data with the column names being the transformed features.
        """
        pipeline = self.get_single_pipeline(pipeline_id)
        problem_specification_stage = pipeline.find_stage_by_type(StageType.problem_specification)[0]
        horizons = cast(ProblemSpecificationConfig, problem_specification_stage.config).horizons
        feature_df_dict = {}
        for horizon in tqdm(horizons, desc="Fetching Data"):
            data = self.client.get(
                Endpoints.FEATURE_DATA_FOR_STAGE(pipeline_id=pipeline_id, stage_id=stage_id, horizon=horizon), download=True,
            )
            feature_df_dict[str(horizon)] = pd.read_csv(StringIO(data), index_col="time")

        terminal_messages.print_success(f"Retrieved Feature Data for Pipeline {pipeline_id} and Stage {stage_id}")
        return feature_df_dict

    @catch_errors
    def download_backtest_info_for_stage(self, pipeline_id: int, stage_id: int, verbose=True) -> Dict[str, pd.DataFrame]:
        """
        Downloads the backtest data of a backtest stage as a data frame. Only validation data is shown.

        df columns:
            - truth: the true value at the given time stamp
            - mean: mean prediction at the given time stamp
            - bound_low: lower bound prediction at the given time stamp (3std)
            - bound_high: higher bound prediction at the given time stamp (3std)
            - backtest: The backtest number. This is set by the n_backtests configuration in the backtest stage.
            - verbose: Log output to terminal?


        WARNING: This is not the same as the expert_backtests; the backtests are finite and discrete here.
        For every-point-rolling retrain backtests please run the expert backtest function, which can
        backtest with retrains between any two arbitrary rows.


        :param pipeline_id: ID of a pipeline
        :param stage_id: ID of a stage - MUST BE A BACKTEST STAGE
        :return: Dictionary of Dataframe of backtest data, indexed by Horizon.
        """
        pipeline = self.get_single_pipeline(pipeline_id)
        problem_specification_stage = pipeline.find_stage_by_type(StageType.problem_specification)[0]
        horizons = cast(ProblemSpecificationConfig, problem_specification_stage.config).horizons
        backtest_df_dict = {}

        if verbose:
            pbar = tqdm(desc="Fetching Data")
        else:
            pbar = None

        for horizon in horizons:
            if pbar and verbose:
                pbar.update()

            data = self.client.get(
                Endpoints.BACKTEST_DATA_FOR_STAGE(pipeline_id=pipeline_id, stage_id=stage_id, horizon=horizon), download=True,
            )
            backtest_df_dict[str(horizon)] = pd.read_csv(StringIO(data), index_col="time")

        if verbose:
            terminal_messages.print_success(f"Retrieved Feature Backtest for Pipeline {pipeline_id} and Stage {stage_id}")
        return backtest_df_dict

    @catch_errors
    def run_expert_backtest_for_validation_data(
        self, pipeline_id: int, stage_id: int, horizon: int, dataset_id: int, n_training_rows_for_backtest: int = 40, verbose=True
    ) -> pd.DataFrame:
        """
        EXPERT FUNCTIONALITY - Not exposed in the Horizon User Interface!

        Runs a rolling retrain across the whole validation data. This is a synchronous request that might take a very long
        time to compute; n different models are trained, where there are n points in the training data.

        df columns:
            - truth: the true value at the given time stamp
            - mean: mean prediction at the given time stamp
            - bound_low: lower bound prediction at the given time stamp (3std)
            - bound_high: higher bound prediction at the given time stamp (3std)
            - backtest: The backtest number. This is set by the n_backtests configuration in the backtest stage.
            - timestamps: Timestamp


        :param n_training_rows_for_backtest: Number of rows to train on for each rolling train / backtest
        :param pipeline_id: ID of a pipeline
        :param stage_id: ID of a stage
        :param dataset_id: ID of the dataset associated with the pipeline
        :param horizon: Forecast horizon to run backtests over
        :param verbose: print to console
        :return: Dataframe of backtest results

        """

        pipeline = self.get_single_pipeline(pipeline_id=pipeline_id)
        problem_specification_stage = pipeline.find_stage_by_type(StageType.problem_specification)[0]
        config = cast(ProblemSpecificationConfig, problem_specification_stage.config)
        data_interface = DataInterface(self.client)
        dataset = data_interface.get_dataset(dataset_id)
        assert dataset.summary.name == pipeline.summary.dataset_name, "Dataset id specified is different to the pipeline id"

        assert int(config.target_feature) in dataset.summary.column_ids, "Dataset id specified is different to the pipeline id"

        n_rows_target = [col.n_rows for col in dataset.analysis if str(col.id_) == str(config.target_feature)][0]

        n_rows_validation = int(np.ceil(config.data_split * n_rows_target))

        assert n_rows_validation / 2 > n_training_rows_for_backtest, "Too many training rows selected"
        assert n_training_rows_for_backtest > 20, "Please select at lease 20 training rows"

        return self.run_expert_backtest_between_two_rows(
            horizon=horizon,
            start_row=n_rows_target,
            end_row=n_rows_validation,
            n_training_rows_for_backtest=n_training_rows_for_backtest,
            pipeline_id=pipeline_id,
            stage_id=stage_id,
            verbose=verbose,
        )

    def run_expert_backtest_between_two_rows(
        self, horizon: int, start_row: int, end_row: int, n_training_rows_for_backtest: int, pipeline_id: int, stage_id: int, verbose=True
    ):
        """

        EXPERT FUNCTIONALITY - Not exposed in the Horizon User Interface!

        WARNING: This function contains no guards to ensure that the rows are not in the feature training data. The method
                 run_expert_backtest_for_validation_data ensures that the backtests are run over valid rows.

        Runs a rolling retrain between two rows. This is a synchronous request that might take a very long
        time to compute; n different models are trained, where there are n points in the training data.

        df columns:
            - truth: the true value at the given time stamp
            - mean: mean prediction at the given time stamp
            - bound_low: lower bound prediction at the given time stamp (3std)
            - bound_high: higher bound prediction at the given time stamp (3std)
            - backtest: The backtest number. This is set by the n_backtests configuration in the backtest stage.
            - timestamps: Timestamp

        :param horizon: Forecast horizon to run backtests over
        :param start_row: Row to start backtest
        :param end_row: Row to backtest to
                :param n_training_rows_for_backtest: Number of rows to train on for each rolling train / backtest
        :param pipeline_id: ID of a pipeline
        :param stage_id: ID of a stage
        :param verbose: print to console

        :return:  Dataframe of backtest results
        """

        if verbose:
            terminal_messages.print_expert_message(f"Initialising Backtest from row {end_row} to row {start_row} (Pipeline {pipeline_id})")

        response = self.client.get(
            Endpoints.EXPERT_BACKTEST_FOR_STAGE_AND_HORIZON(
                pipeline_id=pipeline_id,
                horizon=horizon,
                first_row=end_row,
                last_row=start_row,
                n_training_rows=n_training_rows_for_backtest,
                stage_id=stage_id,
            )
        )

        if verbose:
            terminal_messages.print_success("Expert Backtest Complete")

        df = pd.DataFrame.from_dict(convert_dict_from_camel_to_snake(response),)
        df.drop("neg_rmse", axis=1, inplace=True)
        df.set_index("timestamps", inplace=True)
        df.index = pd.to_datetime(df.index)
        return df

    def get_future_predictions_for_stage(self, pipeline_id: int, stage_id: int) -> pd.DataFrame:
        """
        Gets the future predictions for a prediction stage

        df columns:
            - mean: mean prediction at the given time stamp
            - bound_low: lower bound prediction at the given time stamp (3std)
            - bound_high: higher bound prediction at the given time stamp (3std)

        :param pipeline_id: ID of a pipeline
        :param stage_id: ID of a stage - MUST BE A PREDICTION STAGE
        :return:
        """
        insight = self.get_insight_for_stage(pipeline_id=pipeline_id, stage_id=stage_id)
        df = pd.DataFrame.from_records([convert_dict_from_camel_to_snake(prediction) for prediction in insight["predictions"]])
        df.set_index("date", inplace=True)
        return df

    @catch_errors
    def delete_pipelines(self, pipeline_ids: List[int]):
        """
        Deletes pipelines as identified by their identifiers.
        These may be retrieved by calling DataInterface.list_pipelines.

        :param identifiers: list of numeric pipeline identifiers
        :return:
        """

        pbar = tqdm(pipeline_ids)
        for identifier in pbar:
            pbar.set_description(f"Deleting Pipeline Set with ID: {identifier}")
            # self.client.delete(Endpoints.SINGLE_PIPELINE(identifier))
            self.client.delete(Endpoints.SINGLE_PIPELINE(identifier))

    def delete_all_pipelines(self):
        """
        Deletes all pipelines owned by the current user.

        WARNING: Calling this endpoint is a permanent action and cannot be undone.

        :return:
        """
        pipelines = self.list_pipelines()
        pipeline_ids = [pipeline.summary.id_ for pipeline in pipelines]
        self.delete_pipelines(pipeline_ids)

    ## EXPERIMENTAL FUNCTIONS BELOW THIS LINE.

    def add_stage_to_end_of_pipeline(self, pipeline_id: int, stage_type: StageType) -> Pipeline:
        """
        EXPERIMENTAL

        Adds a stage to the end of a pipeline.

        :param pipeline_id: Unique pipeline identifier
        :param stage_type: Type of stage to add
        :param config: Optional stage configuration
        :return: Pipeline with new stage added
        """

        body = {"parentStage": None, "stageType": stage_type.name}

        pipeline = construct_pipeline_class(self.client.put(Endpoints.STAGES(pipeline_id), json=body,))

        return self.get_single_pipeline(pipeline.summary.id_)

    def run_multitarget_forecast(
        self,
        pipeline_template: Pipeline,
        *,
        column_names: List = -1,  # type: ignore
        column_ids: List = -1,  # type: ignore
        n_training_rows_for_one_point_backtest=None,
        one_point_backtests=False,
    ) -> Dict[str, pd.DataFrame]:
        """

        EXPERIMENTAL - NEEDS HEAVY REFACTORING

        Creates a multi target forecast by looping through all specified targets.

        Feature engineering is run independently for each target.

        :param n_training_rows_for_one_point_backtest: Number of training rows to use for the regressor
        :param pipeline_template: The pipeline template to be used for creating new pipelines
        :param column_names: List of names of columns to run analysis with. Do not specify this and ids together.
        :param column_ids: List of ids of columns to run analysis with. Do not specify this and names together.
        :param one_point_backtests: Runs expert backtests. If false then n_training_rows_for_one_point_backtest is ignored.

        :return:
        """
        assert column_names == -1 or column_ids == -1, "Please only specify one of column_ids or column_names"

        terminal_messages.print_expert_message(
            "This feature is experimental and can be very computationally intensive."
            "Please ensure that you have no queued or pending pipelines prior to "
            "running this method."
        )

        if column_ids == -1:
            column_ids = [column.id_ for column in pipeline_template.dataset.columns if column.name in column_names]  # type: ignore

        if column_names == -1:
            column_names = [column.name for column in pipeline_template.dataset.columns if str(column.id_) in column_ids]  # type: ignore

        pipeline_ids = []
        pbar = tqdm(total=len(column_ids))
        pbar.set_description(f"\nRunning Multitarget Forecast")

        forecasts = []
        backtests = []

        for column_id, column_name in zip(column_ids, column_names):
            pbar.update()
            pipeline = self.create_pipeline(
                dataset_id=pipeline_template.dataset.id_,
                blueprint=BlueprintType[pipeline_template.summary.blueprint],
                name=f"{pipeline_template.summary.name}::TARGET={column_name}",
            )

            pipeline_ids.append(pipeline.summary.id_)

            for stage, template_stage in zip(pipeline.stages, pipeline_template.stages):
                self.update_config(
                    pipeline_id=pipeline.summary.id_, stage_id=stage.id_, config=template_stage.config,
                )
                self.update_config(
                    pipeline_id=pipeline_template.summary.id_, stage_id=template_stage.id_, config=template_stage.config,
                )

            config = pipeline.find_stage_by_type(StageType.problem_specification)[0].config
            config = cast(ProblemSpecificationConfig, config)
            config.target_feature = str(column_id)

            pipeline = self.run_pipeline(pipeline_id=pipeline.summary.id_, synchronous=True, verbose=False)

            forecast = self.get_future_predictions_for_stage(pipeline_id=pipeline.summary.id_, stage_id=pipeline.last_completed_stage.id_)

            forecast.index = pd.to_datetime(forecast.index.astype(int) * 1000000)
            forecast["Series"] = column_name
            forecasts.append(forecast)

            problem_specification_stage = pipeline.find_stage_by_type(StageType.problem_specification)[0]
            problem_specification_config = cast(ProblemSpecificationConfig, problem_specification_stage.config)

            backtest = self.run_backtesting_for_multitarget(
                n_training_rows_for_one_point_backtest, one_point_backtests, pipeline, problem_specification_config
            )

            backtest.columns = backtest.columns + "::" + column_name
            backtests.append(backtest)

        all_backtests = pd.concat(backtests, axis=1, sort=False)
        all_forecasts = pd.concat(forecasts, axis=0, sort=False)

        self.delete_pipelines(pipeline_ids=[pipeline_template.summary.id_])

        return {"backtests": all_backtests, "forecasts": all_forecasts}

    def run_backtesting_for_multitarget(
        self, n_training_rows_for_one_point_backtest, one_point_backtests, pipeline, problem_specification_config
    ):
        if one_point_backtests:
            backtest = self.run_expert_backtest_for_validation_data(
                pipeline_id=pipeline.summary.id_,
                stage_id=pipeline.find_stage_by_type(StageType.backtest)[0].id_,
                horizon=problem_specification_config.horizons[0],
                dataset_id=pipeline.dataset.id_,
                n_training_rows_for_backtest=n_training_rows_for_one_point_backtest or 30,
                verbose=False,
            )
        else:
            backtest_dict = self.download_backtest_info_for_stage(
                pipeline_id=pipeline.summary.id_, stage_id=pipeline.find_stage_by_type(StageType.backtest)[0].id_, verbose=False,
            )

            backtest = backtest_dict[str(problem_specification_config.horizons[0])]
        return backtest

    def run_multitarget_forecast_with_target_specific_feature_set(
        self,
        pipeline_template: Pipeline,
        *,
        column_names: List = -1,  # type: ignore
        column_ids: List = -1,  # type: ignore
        n_training_rows_for_one_point_backtest=None,
        one_point_backtests=False,
    ) -> Dict[str, pd.DataFrame]:
        """

        EXPERIMENTAL - NEEDS HEAVY REFACTORING

        Creates a multi target forecast by looping through all specified targets.

        Feature engineering is run ONCE for the specified target

        :param one_point_backtests: Runs expert backtests. If false then n_training_rows_for_one_point_backtest is ignored.
        :param n_training_rows_for_one_point_backtest: Number of training rows to use for the regressor
        :param pipeline_template: The pipeline template to be used for creating new pipelines
        :param column_names: List of names of columns to run analysis with. Do not specify this and ids together.
        :param column_ids: List of ids of columns to run analysis with. Do not specify this and names together.
        :return: Dictionary of results
        """

        assert column_names == -1 or column_ids == -1, "Please only specify one of column_ids or column_names"

        terminal_messages.print_expert_message(
            "This feature is experimental and can be very computationally intensive. "
            "Please ensure that you have no queued or pending pipelines prior to "
            "running this method."
        )

        pipeline_columns = pipeline_template.dataset.columns

        if column_ids == -1:
            column_ids = [column.id_ for column in pipeline_columns if column.name in column_names]  # type: ignore

        if column_names == -1:
            column_names = [column.name for column in pipeline_columns if str(column.id_) in column_ids]  # type: ignore

        template_problem_spec_config = pipeline_template.find_stage_by_type(StageType.problem_specification)[0].config
        template_problem_spec_config = cast(ProblemSpecificationConfig, template_problem_spec_config)

        assert len(template_problem_spec_config.horizons) == 1, "Multi-Target is only supported for a one-step prediction."

        pipeline = self.get_single_pipeline(pipeline_id=pipeline_template.summary.id_)

        for stage, template_stage in zip(pipeline.stages, pipeline_template.stages):
            self.update_config(
                pipeline_id=pipeline.summary.id_, stage_id=stage.id_, config=template_stage.config,
            )

        terminal_messages.print_update("Running Template Pipeline for Feature Discovery")
        self.run_pipeline(pipeline_id=pipeline.summary.id_, synchronous=True)

        pipeline = self.get_single_pipeline(pipeline_id=pipeline.summary.id_)
        terminal_messages.print_success("Successfully run feature generation. Exporting Data.")

        features = self.download_feature_info_for_stage(pipeline_id=pipeline.summary.id_, stage_id=pipeline.last_completed_stage.id_)
        original_data = self.download_feature_info_for_stage(pipeline_id=pipeline.summary.id_, stage_id=pipeline.stages[0].id_)

        augmented_features = pd.concat(features.values(), axis=1, sort=False)
        augmented_features = pd.concat([augmented_features, *original_data.values()], axis=1, sort=False)
        augmented_features_no_duplicates = augmented_features.loc[:, ~augmented_features.columns.duplicated()]
        augmented_features_no_duplicates.reset_index(inplace=True)

        data_interface = DataInterface(self.client)

        augmented_dataset = data_interface.upload_data(
            data=augmented_features_no_duplicates, name=f"OUTPUT_FEATURES::{pipeline.summary.name}"
        )

        pipeline_ids = []
        pbar = tqdm(total=len(column_ids))
        pbar.set_description(f"\nRunning Multitarget Forecast")

        forecasts = []
        backtests = []

        for column_name in column_names:
            pbar.update()
            pipeline = self.create_pipeline(
                dataset_id=augmented_dataset.summary.id_,
                blueprint=BlueprintType.stationarisation,
                name=f"TARGET={column_name}::TEMPLATE={pipeline_template.summary.name}",
            )

            pipeline_ids.append(pipeline.summary.id_)

            new_problem_spec_config = pipeline.find_stage_by_type(StageType.problem_specification)[0].config
            new_problem_spec_config.target_feature = [
                column.id_ for column in augmented_dataset.summary.columns if column.name == column_name  # type: ignore
            ][0]
            new_problem_spec_config.horizons = template_problem_spec_config.horizons

            self.update_config(
                pipeline_id=pipeline.summary.id_,
                stage_id=pipeline.find_stage_by_type(StageType.problem_specification)[0].id_,
                config=new_problem_spec_config,
            )

            stationarisation_stage = pipeline.find_stage_by_type(StageType.stationarisation)[0]
            stationarisation_config = cast(StationarisationStageConfig, stationarisation_stage.config)
            stationarisation_config.strategy = StationarisationStrategy.none

            self.update_config(pipeline_id=pipeline.summary.id_, stage_id=stationarisation_stage.id_, config=stationarisation_config)

            pipeline = self.add_stage_to_end_of_pipeline(pipeline_id=pipeline.summary.id_, stage_type=StageType.backtest)

            self.add_stage_to_end_of_pipeline(pipeline_id=pipeline.summary.id_, stage_type=StageType.prediction)

            if len(pipeline_template.find_stage_by_type(StageType.backtest)) > 0:
                backtest_stage = pipeline_template.find_stage_by_type(StageType.backtest)[0]
                backtest_config = backtest_stage.config
                self.update_config(
                    pipeline_id=pipeline.summary.id_,
                    stage_id=pipeline.find_stage_by_type(StageType.backtest)[0].id_,
                    config=backtest_config,
                )

            pipeline_ids.append(pipeline.summary.id_)

            pipeline = self.run_pipeline(pipeline_id=pipeline.summary.id_, synchronous=True, verbose=False,)
            forecast = self.get_future_predictions_for_stage(pipeline_id=pipeline.summary.id_, stage_id=pipeline.last_completed_stage.id_)

            forecast.index = pd.to_datetime(forecast.index.astype(int) * 1000000)
            forecast["Series"] = column_name
            forecasts.append(forecast)

            backtest = self.run_backtesting_for_multitarget(
                n_training_rows_for_one_point_backtest or 30, one_point_backtests, pipeline, new_problem_spec_config,
            )

            backtest.columns = backtest.columns + "::" + column_name
            backtests.append(backtest)

        all_backtests = pd.concat(backtests, axis=1, sort=False)
        all_forecasts = pd.concat(forecasts, axis=0, sort=False)

        return {"backtests": all_backtests, "forecasts": all_forecasts}
