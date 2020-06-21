import requests
from mf_horizon_client.client.datasets.data_interface import DataInterface
from mf_horizon_client.client.pipelines.pipeline_interface import PipelineInterface
from mf_horizon_client.client.session import HorizonSession
from mf_horizon_client.client.warnings import Warnings
from mf_horizon_client.endpoints import Endpoints

DEFAULT_MAX_RETRIES = 3
DEFAULT_CONCURRENT_TASKS = 1

ENDPOINTS = Endpoints()


class HorizonClient(HorizonSession):
    """Sets up a connection to Horizon.

    Args:
        server_url (str): URL of your Horizon server
        api_key (str): Your personal API key
        max_retries (int, default 3): How many times to retry a request if a connection error occurs.
        max_concurrent_pipelines (str, default 1): The maximum number of pipelines that may be run at any one time.
            This must be set up from the deployment configuration.
    """

    def __init__(
        self,
        server_url: str,
        api_key: str,
        max_retries: int = DEFAULT_MAX_RETRIES,
        max_concurrent_pipelines: int = DEFAULT_CONCURRENT_TASKS,
    ) -> None:

        if server_url[-1] != "/":
            server_url += "/"

        super().__init__(server_url, api_key, max_retries)

        if not max_concurrent_pipelines:
            print(Warnings.NO_MAX_FIRE_AND_FORGET_WORKERS_SPECIFIED)
        self._max_concurrent_tasks = max_concurrent_pipelines
        self.validate_connection()

    def validate_connection(self):
        """
        Checks that the connection is still open and valid
        """
        try:
            self.get(ENDPOINTS.ALL_DATASETS)
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                "Failed to connect to Horizon API - likely network error or incorrect URL. " "Have you included `https://` in the URL?"
            )
        except requests.exceptions.RetryError:
            raise ConnectionError("Failed to connect to Horizon API - likely incorrect API key.")

    def horizon_compute_status(self) -> dict:
        """
        Checks to see how many pipeline runners are not being used
        :return: WorkerStatusSchema
        """
        return self.get(ENDPOINTS.STATUS)

    def data_interface(self) -> DataInterface:
        return DataInterface(self)

    def pipeline_interface(self) -> PipelineInterface:
        return PipelineInterface(self)
