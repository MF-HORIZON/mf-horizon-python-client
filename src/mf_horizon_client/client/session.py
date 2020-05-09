from typing import Any, Dict, Union, cast
from urllib.parse import urljoin

import requests
from requests import Response, Session
from urllib3 import Retry
from requests.adapters import HTTPAdapter
from mf_horizon_client.client.error import HorizonError
from mf_horizon_client.utils.catch_method_exception import catch_errors
from mf_horizon_client.utils.terminal_messages import print_success

RETRY_STATUS_CODES = [500, 501, 502, 503, 504]


class HorizonResponse:
    """Wrapper class for a successful :class:`.Response` received from Horizon."""

    def __init__(self, response: Union[Response, Any]) -> None:
        if isinstance(response, Response):
            if response.ok:
                self.body = response.json()
                return
            else:
                self.body = None
                raise HorizonError(response)

        self.body = response


class HorizonSession:
    """Wrapper class for a :class:`.Session` that makes requests to the Horizon API.

    Args:
        server_url (str): URL of your Horizon server
        auth0_bearer_token (str): Your personal API key
        max_retries (int, default 3): How many times to retry a request if a connection error occurs.
    """

    def __init__(self, server_url: str, auth0_bearer_token: str, max_retries: int = 3):
        headers = {"authorization": f"Bearer {auth0_bearer_token}"}
        self._session: Session = self._make_session(server_url, max_retries, headers)
        self._root_url = server_url

    @staticmethod
    def _make_session(server_url: str, max_retries: int, headers) -> Session:
        session = Session()
        retry = Retry(
            total=max_retries, connect=max_retries, backoff_factor=0.5, method_whitelist=False, status_forcelist=RETRY_STATUS_CODES,
        )

        adapter = HTTPAdapter(max_retries=retry)
        session.mount(server_url, adapter)
        session.headers = headers
        return session

    @catch_errors
    def post(self, endpoint: str, body: dict = None, files: Dict = None, on_success_message: str = None,) -> HorizonResponse:
        """Make a POST request to Horizon with a JSON body.

        Args:
            endpoint: Endpoint for the request (will be appended to the server_url).
            body: Request body in JSON format.
            files: File for file upload.
            on_success_message: message to print if successful request

        Returns:
            The :class:`.HorizonResponse` to the request.

        Raises:
            :class:`.HorizonError` if an error response is received.
        """

        response = self._session.post(urljoin(base=self._root_url, url=endpoint), data=body, files=files,)

        if on_success_message and response.ok:
            print_success(on_success_message)

        return HorizonResponse(response).body

    @catch_errors
    def put(self, endpoint: str, body: dict = None, json: dict = None) -> HorizonResponse:
        """Make a PUT request to Horizon with a JSON body.

        Args:
            endpoint (str): Endpoint for the request (will be appended to the server_url).
            body (dict): Request body in JSON format.
            json (dict): Requests json arg

        Returns:
            The :class:`.HorizonResponse` to the request.

        Raises:
            :class:`.HorizonError` if an error response is received.
        """

        url = urljoin(base=self._root_url, url=endpoint)

        return HorizonResponse(self._session.put(url, data=body, json=json)).body

    def get(self, endpoint: str, query_params: Dict = None, download: bool = False) -> Any:
        """Make a GET request to Horizon

        Args:
            endpoint: Endpoint for the request (will be appended to the server_url).
            query_params: Query parameters in Dict format (will be appended to the url).
            download: True if request returns download blob.

        Returns:
            The :class:`.HorizonResponse` to the request.

        Raises:
            :class:`.HorizonError` if an error response is received.
        """
        url = requests.Request("GET", urljoin(base=self._root_url, url=endpoint), params=query_params).prepare().url

        url = cast(str, url)

        if download:
            try:
                return self._session.get(url).text
            except Exception:  # pylint: disable=broad-except
                pass
        return HorizonResponse(self._session.get(url)).body

    def delete(self, endpoint: str) -> HorizonResponse:
        """Make a DELETE request to Horizon

        Args:
            endpoint (str): Endpoint for the request (will be appended to the server_url).

        Returns:
            The :class:`.HorizonResponse` to the request.

        Raises:
            :class:`.HorizonError` if an error response is received.
        """
        return HorizonResponse(self._session.delete(urljoin(base=self._root_url, url=endpoint)),)

    def disconnect(self):
        self._session.close()
