import logging
from pathlib import Path

import pkg_resources

logger = logging.getLogger(__name__)


def test_data_included_with_package():
    iris_datapath = Path(
        pkg_resources.resource_filename("mf_horizon_client", "datasets/iris/iris.csv")
    )

    logger.info(f"Found data at {iris_datapath}")

    assert iris_datapath.exists()
    assert iris_datapath.is_file()
