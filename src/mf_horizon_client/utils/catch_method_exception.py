import functools

from mf_horizon_client.client.error import HorizonError
from mf_horizon_client.utils.terminal_messages import (
    print_failure,
    print_server_error_details,
)


def catch_errors(f):
    """
    Catches a class-method exception - to be used as a decorator
    """

    @functools.wraps(f)
    def func(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except HorizonError as exception:
            print_failure(f"{str.upper(f.__name__)} request failed to successfully execute. {exception.status_code if exception else None}")
            if exception and exception.message:
                print_server_error_details(exception.message)

    return func
