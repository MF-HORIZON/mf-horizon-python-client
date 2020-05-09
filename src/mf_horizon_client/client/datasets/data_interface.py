import io
import json
from typing import List

import dataclasses
import numpy as np
import pandas as pd
from tqdm import tqdm
from mf_horizon_client.data_structures.column_passport import ColumnPassport
from mf_horizon_client.data_structures.dataset_summary import DatasetSummary
from mf_horizon_client.data_structures.individual_dataset import IndividualDataset
from mf_horizon_client.data_structures.raw_column import RawColumn
from mf_horizon_client.endpoints import Endpoints
from mf_horizon_client.utils.catch_method_exception import catch_errors
from mf_horizon_client.utils.string_case_converters import convert_dict_from_camel_to_snake
from mf_horizon_client.utils.terminal_messages import print_success, print_warning


class DataInterface:
    def __init__(self, client):
        """
        :param client: HorizonClient
        """
        self.client = client

    def upload_data(
        self,
        data: pd.DataFrame,
        name: str,
        forward_fill_missing_values: bool = False,
        replace_missing_values: bool = False,
        encode_categorical_data: bool = False,
        max_categories: int = 5,
        align_to_column: str = "",
    ) -> IndividualDataset:
        """
        Uploads the given data set to the Horizon API.

        :param align_to_column: Aligns data to column if the data is misaligned. This should be selected as the target
        if data is misaligned or has missing values. Selecting this will also cause missing data in the specified
        column to be dropped.
        :param data: DataFrame to be uploaded
        :param name: Name of the data set to be uploaded
        :param forward_fill_missing_values: Forward-fill missing values
        :param replace_missing_values: Replace missing values
        :param encode_categorical_data: Categorically encode data that is non-numeric
        :param max_categories: Maximum number of categories per series.
        :return: A summary of the uploaded data set.
        """

        str_buffer = io.StringIO(data.to_csv(encoding="utf-8", index=False))
        str_buffer.seek(0)
        str_buffer.name = name

        if forward_fill_missing_values and not align_to_column:
            print_warning(
                "Forward-fill select without alignment to column. Please be aware that "
                "if you choose a target column that has been forward-filled this will yield "
                "scientifically inaccurate results"
            )

        options = {
            "alignTo": align_to_column,
            "missingDataStrategy": {
                "ffill": {"enabled": forward_fill_missing_values},
                "replaceMissing": {"enabled": replace_missing_values, "replaceWith": 1},
            },
            "nonNumericStrategy": {"encode": {"enabled": encode_categorical_data, "maxCategories": max_categories}},
        }

        request_data = dict(file=str_buffer, follow_redirects=True)
        data = dict(options=json.dumps(options))

        response = self.client.post(
            endpoint=Endpoints.UPLOAD_DATA, body=data, files=request_data, on_success_message=f"Data set '{name}' uploaded",
        )

        dataset_summary = DatasetSummary(**convert_dict_from_camel_to_snake(response))
        dataset = self.get_dataset(dataset_summary.id_)

        return dataset

    @catch_errors
    def list_datasets(self) -> List[DatasetSummary]:
        """
        requests a list of datasets (DatasetSchema) that have been uploaded into horizon. The data itself is not returned - just
        the metadata.

        """

        datasets = self.client.get(Endpoints.ALL_DATASETS)
        return [DatasetSummary(**convert_dict_from_camel_to_snake(dataset)) for dataset in datasets]

    @catch_errors
    def delete_datasets(self, identifiers: List[int] = None):
        """
        Deletes data sets as identified by their identifiers.
        These may be retrieved by calling DataInterface.list_datasets.

        :param identifiers: list of numeric identifiers
        :return:
        """

        pbar = tqdm(identifiers)
        for identifier in pbar:
            pbar.set_description(f"Deleting Data Set with ID: {identifier}")
            self.client.delete(Endpoints.SINGLE_DATASET(identifier))

    @catch_errors
    def delete_all_datasets(self):
        """
        Deletes all data sets previously uploaded by the authorised user.

        WARNING: All associated pipelines will also be deleted.
        WARNING: Calling this endpoint is effectively the same as resetting Horizon for a user.

        :return:
        """

        datasets = self.list_datasets()
        dataset_ids = [dataset.id_ for dataset in datasets]
        self.delete_datasets(dataset_ids)
        print_success("All data successfully deleted from Horizon!")

    @catch_errors
    def rename_dataset(self, identifier: int, name: str):
        """
        Renames an already existing dataset
        :param identifier: id of a dataset
        :param name: The new name for the dataset
        :return:
        """

        assert len(name) < 100, "Name too long. Please keep to under 100 chars."

        self.client.put(Endpoints.RENAME_DATASET(identifier), body={"newName": name})

    @catch_errors
    def get_dataset(self, identifier: int) -> IndividualDataset:
        """
        Gets a single data set's meta data.

        :param identifier: dataset id as returned from upload_dataset or list_all_datasets.
        :return: Individual data set sans data
        """

        response = self.client.get(Endpoints.SINGLE_DATASET(identifier))

        individual_dataset_dictionary = response
        column_data = [ColumnPassport(**convert_dict_from_camel_to_snake(col)) for col in individual_dataset_dictionary["analysis"]]
        dataset = IndividualDataset(
            analysis=column_data, summary=DatasetSummary(**convert_dict_from_camel_to_snake(individual_dataset_dictionary["summary"]),),
        )

        dataset.summary.columns = [RawColumn(name=col.name, id_=col.id_) for col in column_data]

        return dataset

    @catch_errors
    def get_series_data_sampled(self, dataset_identifier: int, series_identifier: int):
        """
        Retrieves sampled data of a particular series in a data set. Suitable for plotting.

        In the case of intra-day data this data is aggregated into a daily plot.

        :param dataset_identifier: Unique identifier of a dataset.
        :param series_identifier: Unique identifier of a column
        :return:
        """

        response = self.client.get(Endpoints.SINGLE_SERIES(dataset_identifier, series_identifier))

        return convert_dict_from_camel_to_snake(response)

    @catch_errors
    def get_correlations(self, dataset_identifier: int, series_identifier: int):
        """
        Calculates the pearson correlation of a single series with every other series in a dataset

        :param dataset_identifier: Unique identifier of a dataset.
        :param series_identifier: Unique identifier of a column
        :return:
        """

        dataset_summary = self.get_dataset(dataset_identifier)
        names = [col.name for col in dataset_summary.analysis if col.id_ == series_identifier]
        if len(names) == 0:
            raise ValueError("Invalid series identifier specified")
        series_name = names[0]
        correlation_data = self.client.get(Endpoints.SINGLE_SERIES_CORRELATIONS_WITH_OTHER_SERIES(dataset_identifier, series_identifier))
        correlations = pd.DataFrame.from_dict(correlation_data["data"])
        correlations.columns = ["Series", "Pearson Correlation"]
        correlations.name = series_name
        return correlations

    @catch_errors
    def get_autocorrelation(self, dataset_identifier: int, series_identifier: int):
        """
        Calculates the autocorrelation functon of a single series

        :param dataset_identifier: Unique identifier of a dataset.
        :param series_identifier: Unique identifier of a column
        :returndT:
        """
        dataset_summary = self.get_dataset(dataset_identifier)
        names = [col.name for col in dataset_summary.analysis if col.id_ == series_identifier]
        if len(names) == 0:
            raise ValueError("Invalid series identifier specified")

        series_name = names[0]
        acf = self.client.get(Endpoints.SINGLE_SERIES_AUTOCORRELATION(dataset_identifier, series_identifier))
        acf_df = pd.DataFrame(acf["data"])
        acf_df.columns = ["Lag", f"Correlation: f{series_name}"]
        return acf_df

    @catch_errors
    def get_stationarity_scores(self, dataset_identifier: int) -> pd.DataFrame:
        """
        Returns the Augmented-dicky-fuller ADF score of the signals in a data set. For large data a data sample is used to compute this.

        :param dataset_identifier: Unique identifier of a dataset
        :return: Dataframe of stationarity scores
        """

        dataset = self.get_dataset(identifier=dataset_identifier)
        df = pd.DataFrame.from_records([dataclasses.asdict(series) for series in dataset.analysis])[["id_", "name", "adf"]]
        df["id_"] = df["id_"].astype(str)
        return df

    @catch_errors
    def correlation_matrix(self, dataset_identifier: int):
        dataset_summary = self.get_dataset(dataset_identifier)
        ids = [col.id_ for col in dataset_summary.analysis]
        names = [col.name for col in dataset_summary.analysis]

        matrix = np.zeros((len(names), len(names)))

        pbar = tqdm(ids)
        pbar.set_description()

        for index, id_ in enumerate(pbar):
            pbar.set_description(f"Correlation Matrix: Processing {names[index]}")
            name = [col.name for col in dataset_summary.analysis if col.id_ == id_][0]
            df = self.get_correlations(dataset_identifier, id_)
            self_correlation = pd.DataFrame({"Series": name, "Pearson Correlation": 1}, index=[index])
            single_slice = pd.concat([df.iloc[:index], self_correlation, df.iloc[index:]]).reset_index(drop=True)
            matrix[index] = single_slice.iloc[:, 1].to_numpy()

        return pd.DataFrame(matrix, columns=names)

    @catch_errors
    def get_mutual_information(self, dataset_identifier: int, series_identifier: int):
        """
        Calculates the mutual information of a single series with all other columns in a dataset


        :param dataset_identifier: Unique identifier of a dataset.
        :param series_identifier: Unique identifier of a column
        :return:
        """
        dataset_summary = self.get_dataset(dataset_identifier)
        names = [col.name for col in dataset_summary.analysis if col.id_ == series_identifier]
        if len(names) == 0:
            raise ValueError("Invalid series identifier specified")
        series_name = names[0]
        mutual_information_data = self.client.get(
            Endpoints.SINGLE_SERIES_MUTUAL_INFORMATION_WITH_OTHER_SERIES(dataset_identifier, series_identifier)
        )
        mutual_information_data = pd.DataFrame.from_dict(mutual_information_data["data"])
        mutual_information_data.columns = ["Series", "Mutual Information"]
        mutual_information_data.name = series_name
        return mutual_information_data

    @catch_errors
    def upload_data_long_format_as_single_data_set(
        self,
        data: pd.DataFrame,
        name: str,
        cross_section_column_name: str,
        date_column_name: str,
        replace_missing_values: bool = True,
        forward_fill_missing_values: bool = False,
        encode_categorical_data=True,
        max_categories=5,
    ) -> IndividualDataset:
        """
        Uploads long format data into Horizon. The data frame should have a date column, with a numeric index.

        :param data: The dataset in a pandas data frame. Must have a valid date column.
        :param name: Name of the data set to be uploaded
        :param cross_section_column_name: The identifier column that groups the records
        :param date_column_name: The column name of the date index.
        :param forward_fill_missing_values: Forward-fill missing values
        :param replace_missing_values: Replace missing values
        :return: A summary of the uploaded data set.
        :param encode_categorical_data: Categorically encode data that is non-numeric
        :param max_categories: Maximum number of categories per series.
        """

        df = data.pivot_table(columns=cross_section_column_name, index=date_column_name)
        df.reset_index(inplace=True)
        df.columns = ["/".join(column) for column in df.columns]

        return self.upload_data(
            data=df,
            name=name,
            forward_fill_missing_values=forward_fill_missing_values,
            replace_missing_values=replace_missing_values,
            encode_categorical_data=encode_categorical_data,
            max_categories=max_categories,
        )
