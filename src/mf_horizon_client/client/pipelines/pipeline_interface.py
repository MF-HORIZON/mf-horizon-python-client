import json
from io import StringIO
from time import sleep
from typing import Any, Dict, List, cast, Union

import numpy as np
import pandas as pd
from tqdm import tqdm
from mf_horizon_client.post_processing.backtests import binary_backtests_returns, calculate_metrics, recommender
from mf_horizon_client.data_structures.feature_id import FeatureId
from mf_horizon_client.client.datasets.data_interface import DataInterface
from mf_horizon_client.client.pipelines.blueprints import BlueprintType
from mf_horizon_client.client.pipelines.construct_pipeline_class import construct_pipeline_class
from mf_horizon_client.data_structures.configs.stage_config import (
    ProblemSpecificationConfig,
    StageConfig,
)
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
    def create_pipeline(self, dataset_id: int, blueprint: BlueprintType, name: str, delete_after_creation=False,) -> Pipeline:
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
        :param delete_after_creation: Deletes pipeline immediately after creation if set to true
        """

        pipeline = self.client.put(Endpoints.PIPELINES, json={"name": name, "datasetId": dataset_id, "blueprint": blueprint.name},)
        pipeline = self.get_single_pipeline(construct_pipeline_class(pipeline).summary.id_)

        if delete_after_creation:
            self.delete_pipelines([pipeline.summary.id_])

        return pipeline

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
        config_dict = dict(config=convert_dict_from_snake_to_camel(json.loads(config.as_json())), preview=False)

        self.client.put(
            Endpoints.UPDATE_STAGE_CONFIGURATION(pipeline_id, stage_id), json=config_dict,
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

        total_rows_for_all_data = [col.n_rows for col in dataset.analysis if str(col.id_) == str(config.target_feature)][0]

        validation_start_row = int(np.ceil(config.data_split * total_rows_for_all_data))
        rows_in_validation_set = total_rows_for_all_data - validation_start_row

        assert rows_in_validation_set / 1.2 > n_training_rows_for_backtest, "Too many training rows selected"
        assert n_training_rows_for_backtest > 20, "Please select at least 20 training rows"

        return self.run_expert_backtest_between_two_rows(
            horizon=horizon,
            start_row=validation_start_row,
            end_row=total_rows_for_all_data,
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
            terminal_messages.print_expert_message(f"Initialising Backtest from row {start_row} to row {end_row} (Pipeline {pipeline_id})")

        response = self.client.get(
            Endpoints.EXPERT_BACKTEST_FOR_STAGE_AND_HORIZON(
                pipeline_id=pipeline_id,
                horizon=horizon,
                first_row=start_row,
                last_row=end_row,
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

        :param pipeline_ids: list of numeric pipeline identifiers
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

    def add_stage_to_pipeline(self, pipeline_id: int, parent_stage_id: int, stage_type: StageType,) -> Pipeline:
        """
        EXPERIMENTAL

        Adds a stage after specified parent_stage_id.

        :param pipeline_id: Unique pipeline identifier
        :param parent_stage_id: ID of the stage preceding desired location of added stage
        :param stage_type: Type of stage to add
        :return: Pipeline with new stage added
        """

        body = {"parentStage": parent_stage_id, "stageType": stage_type.name}

        pipeline = construct_pipeline_class(self.client.put(Endpoints.STAGES(pipeline_id), json=body,))

        return self.get_single_pipeline(pipeline.summary.id_)

    def _build_pipeline_from_template(self, target_column_name: str, pipeline_template: Pipeline):
        """
        Takes a pipeline template object and builds a duplicated pipeline copy of the template, with the
        target specified as the column_name.

        :param target_column_name: Name of the target column
        :param pipeline_template: Template pipeline
        :return:
        """

        assert pipeline_template.dataset.columns, "Please pass a fully defined pipeline template using fetch_pipeline."

        target_column_id = [col.id_ for col in pipeline_template.dataset.columns if str(col.name) == target_column_name][0]

        pipeline = self.create_pipeline(
            dataset_id=pipeline_template.dataset.id_,
            blueprint=BlueprintType.custom,
            name=f"{pipeline_template.summary.name}/{target_column_name}",
        )

        index = 0
        problem_specification_stage = pipeline.find_stage_by_type(StageType.problem_specification)[0]
        parent_id = problem_specification_stage.id_

        # Enumerate irritates the type casting
        for template_stage in pipeline_template.stages:

            if index == 0:
                config = pipeline_template.find_stage_by_type(StageType.problem_specification)[0].config
                cast(ProblemSpecificationConfig, config).target_feature = FeatureId(target_column_id)
                self.update_config(
                    pipeline_id=pipeline.summary.id_, stage_id=problem_specification_stage.id_, config=config,
                )
            else:
                pipeline = self.add_stage_to_pipeline(
                    pipeline_id=pipeline.summary.id_, parent_stage_id=parent_id, stage_type=StageType[template_stage.type]
                )

                stage = pipeline.find_stage_by_type(StageType[template_stage.type])[0]
                self.update_config(pipeline_id=pipeline.summary.id_, stage_id=stage.id_, config=template_stage.config)
                parent_id = stage.id_
            index += 1
        return pipeline

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
        Creates a multi target forecast by looping through all specified targets.

        Feature engineering is run independently for each target.

        :param n_training_rows_for_one_point_backtest: Number of training rows to use for the regressor
        :param pipeline_template: The pipeline template to be used for creating new pipelines
        :param column_names: List of names of columns to run analysis with. Do not specify this and ids together.
        :param column_ids: List of ids of columns to run analysis with. Do not specify this and names together.
        :param one_point_backtests: Runs expert backtests. If false then n_training_rows_for_one_point_backtest is ignored.
        """
        assert column_names == -1 or column_ids == -1, "Please only specify one of column_ids or column_names"

        terminal_messages.print_expert_message("Please ensure that you have no queued or pending pipelines.")

        if column_names == -1:
            column_names = [column.name for column in pipeline_template.dataset.columns if str(column.id_) in column_ids]  # type: ignore

        pbar = tqdm(total=len(column_names))
        pbar.set_description("\nRunning Multitarget Forecast")

        forecasts = []
        backtests = []

        for column_name in column_names:
            pbar.update()
            pipeline = self._build_pipeline_from_template(column_name, pipeline_template)
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
            backtest.columns = backtest.columns + "/" + column_name
            backtests.append(backtest)

        all_backtests = pd.concat(backtests, axis=1, sort=False)
        all_forecasts = pd.concat(forecasts, axis=0, sort=False)
        return {"backtests": all_backtests.dropna(), "forecasts": all_forecasts}

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

        Creates a multi target forecast by looping through all specified targets.

        Feature engineering is run ONCE for the specified target

        :param one_point_backtests: Runs expert backtests. If false then n_training_rows_for_one_point_backtest is ignored.
        :param n_training_rows_for_one_point_backtest: Number of training rows to use for the regressor
        :param pipeline_template: The pipeline template to be used for creating new pipelines
        :param column_names: List of names of columns to run analysis with. Do not specify this and ids together.
        :param column_ids: List of ids of columns to run analysis with. Do not specify this and names together.
        :return: Dictionary of results
        """

        pipeline_columns = pipeline_template.dataset.columns

        if column_names == -1:
            column_names = [column.name for column in pipeline_columns if str(column.id_) in column_ids]  # type: ignore

        pipeline = self._build_pipeline_from_template(target_column_name=column_names[0], pipeline_template=pipeline_template)

        for stage, template_stage in zip(pipeline.stages, pipeline_template.stages):
            self.update_config(pipeline_id=pipeline.summary.id_, stage_id=stage.id_, config=template_stage.config)

        terminal_messages.print_update("Running Template Pipeline for Feature Discovery")
        self.run_pipeline(pipeline_id=pipeline.summary.id_, synchronous=True)

        pipeline = self.get_single_pipeline(pipeline_id=pipeline.summary.id_)
        terminal_messages.print_success("Successfully run feature generation. Exporting Data.")

        features = self.download_feature_info_for_stage(pipeline_id=pipeline.summary.id_, stage_id=pipeline.last_completed_stage.id_,)

        original_data = self.download_feature_info_for_stage(pipeline_id=pipeline.summary.id_, stage_id=pipeline.stages[0].id_,)

        augmented_features = pd.concat(features.values(), axis=1, sort=False)
        augmented_features = pd.concat([augmented_features, *original_data.values()], axis=1, sort=False)
        augmented_features_no_duplicates = augmented_features.loc[:, ~augmented_features.columns.duplicated()]
        augmented_features_no_duplicates.reset_index(inplace=True)

        data_interface = DataInterface(self.client)

        augmented_dataset = data_interface.upload_data(
            data=augmented_features_no_duplicates, name=f"Features {pipeline_template.summary.name}",
        )

        template_pipeline_regression_only = self.create_pipeline(
            dataset_id=augmented_dataset.summary.id_,
            blueprint=BlueprintType.time_series_regression,
            name=pipeline_template.summary.name,
            delete_after_creation=True,
        )

        regression_template_problem_spec_config = cast(ProblemSpecificationConfig, template_pipeline_regression_only.stages[0].config,)

        original_template_problem_spec_config = cast(ProblemSpecificationConfig, pipeline_template.stages[0].config,)

        regression_template_problem_spec_config.data_split = original_template_problem_spec_config.data_split
        regression_template_problem_spec_config.horizons = original_template_problem_spec_config.horizons

        return self.run_multitarget_forecast(
            pipeline_template=template_pipeline_regression_only,
            column_names=column_names,
            one_point_backtests=one_point_backtests,
            n_training_rows_for_one_point_backtest=n_training_rows_for_one_point_backtest,
        )

    @catch_errors
    def directional_response_regression(
        self,
        *,
        data: pd.DataFrame,
        target_column: str,
        cross_section_column_name: str,
        date_column_name: str,
        discrete_value_dates: pd.Series = None,
        train_up_to_row: int = None,
        n_training_rows_for_one_point_backtest: Union[str, int] = "auto",
        blueprint_type: BlueprintType = BlueprintType.nonlinear,
        cleanup=True,
    ):
        """

        EXPERIMENTAL - expect API to change

        :param cleanup: Delete data set and pipelines after running
        :param train_up_to_row: Any row after this will be used for validation / backtesting
        :param blueprint_type: Pipeline blueprint type - see BlueprintType. Must be forecasting pipeline.
        :param target_column: Target column to predict
        :param data: data frame to upload
        :param n_training_rows_for_one_point_backtest: Number of training rows to use for the regressor
        :param cross_section_column_name: The identifier column that groups the records
        :param discrete_value_dates: Long-format dates that are discrete points to measure performance against.
        :param date_column_name: The column name of the date index.
        :return: Dictionary of results
        """
        data_interface = DataInterface(self.client)

        cross_section_variables = data[cross_section_column_name]
        unique_cross_section_variables = cross_section_variables.unique().tolist()

        dataset = data_interface.upload_data_long_format_as_single_data_set(
            data=data, name="Panel", cross_section_column_name=cross_section_column_name, date_column_name=date_column_name,
        )

        data_split = train_up_to_row / dataset.summary.n_rows if train_up_to_row else 0.75

        template_pipeline = self.create_pipeline(
            dataset_id=dataset.summary.id_, blueprint=blueprint_type, name="TMP", delete_after_creation=True,
        )

        problem_spec_config = template_pipeline.find_stage_by_type(StageType.problem_specification)[0].config
        problem_spec_config = cast(ProblemSpecificationConfig, problem_spec_config)
        problem_spec_config.data_split = data_split
        problem_spec_config.horizons = [1]

        if n_training_rows_for_one_point_backtest == "auto":
            n_rows_in_validation_data = int((1 - data_split) * dataset.summary.n_rows)
            n_training_rows_for_one_point_backtest = int(n_rows_in_validation_data / 3)

        results = self.run_multitarget_forecast(
            pipeline_template=template_pipeline,
            column_names=["/".join([target_column, var]) for var in unique_cross_section_variables],
            one_point_backtests=True,
            n_training_rows_for_one_point_backtest=n_training_rows_for_one_point_backtest,
        )

        directional_backtests = binary_backtests_returns(results["backtests"])

        backtest_errors = pd.DataFrame()
        average_scores = pd.DataFrame()
        full_metrics = {}

        discrete_values_full_metrics = {}
        discrete_values_average_scores = pd.DataFrame()

        for variable in unique_cross_section_variables:
            # Calculate the continuous price scores
            directions = pd.DataFrame()
            directions["predictions"] = directional_backtests["/".join(["predictions", target_column, variable])]
            directions["truths"] = directional_backtests["/".join(["truth", target_column, variable])]

            # No movement in price --> assume no trading that day and drop the backtests
            directions = directions.replace(0, np.nan).dropna()

            backtest_errors[variable] = directions["predictions"] * directions["truths"]

            classification_metrics = calculate_metrics(y_true=directions["truths"], y_pred=directions["predictions"],)
            average_scores[variable] = pd.Series(
                {"accuracy": classification_metrics["accuracy"], "f1_macro": classification_metrics["macro avg"]["f1-score"],}
            )
            full_metrics[variable] = classification_metrics

            # Calculate the metrics just for reporting dates
            if discrete_value_dates is not None:
                y_discrete = directions[directions.index.isin(discrete_value_dates[discrete_value_dates == variable].index)]

                discrete_values_full_metrics[variable] = calculate_metrics(y_true=y_discrete["truths"], y_pred=y_discrete["predictions"],)

                discrete_values_average_scores[variable] = pd.Series(
                    {
                        "accuracy": discrete_values_full_metrics[variable]["accuracy"],
                        "f1_macro": discrete_values_full_metrics[variable]["macro avg"]["f1-score"],
                    }
                )

        last_observed_values = data[data[date_column_name] == data[date_column_name].max()]
        last_observed_values.index = pd.Series(
            "/".join([target_column, variable]) for variable in last_observed_values[cross_section_column_name]
        )
        last_observed_values = last_observed_values[target_column]

        recommendations = recommender(last_observed_values=last_observed_values, predictions=results["forecasts"],)

        if cleanup:
            data_interface.delete_datasets([dataset.summary.id_])

        return {
            "average_scores": average_scores,
            "full_metrics": full_metrics,
            "discrete_values_full_metrics": discrete_values_full_metrics if discrete_value_dates is not None else -1,
            "discrete_values_average_scores": discrete_values_average_scores if discrete_value_dates is not None else -1,
            "backtests": directional_backtests,
            "continuous_backtests": results["backtests"],
            "predictions": recommendations,
        }
