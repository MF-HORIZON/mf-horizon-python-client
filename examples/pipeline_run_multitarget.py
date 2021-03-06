from typing import cast

import numpy as np
import pandas as pd

from examples.credentials import URL, API_KEY
from mf_horizon_client.client.horizon_client import HorizonClient
from mf_horizon_client.client.pipelines.blueprints import BlueprintType
from mf_horizon_client.data_structures.configs.stage_config import ProblemSpecificationConfig
from mf_horizon_client.data_structures.configs.stage_types import StageType

client = HorizonClient(
    server_url=URL,
    api_key=API_KEY,
    max_retries=1,
)

data_interface = client.data_interface()
pipeline_interface = client.pipeline_interface()

df = pd.DataFrame(pd.date_range("2000", "2004"))

for c in "AB":
    df[c] = np.random.randn(len(df))

dataset = data_interface.upload_data(data=df, name="ALPHABET")

template_pipeline = pipeline_interface.create_pipeline(
    dataset_id=dataset.summary.id_, blueprint=BlueprintType.fast_forecasting, name="MT", delete_after_creation=True
)

problem_spec_config = template_pipeline.find_stage_by_type(StageType.problem_specification)[0].config
problem_spec_config = cast(ProblemSpecificationConfig, problem_spec_config)
problem_spec_config.horizons = [1]
problem_spec_config.data_split = 0.6
template_pipeline.stages[0].config = problem_spec_config

## Run with feature selection tailored for a specific target (faster)
# results = pipeline_interface.run_multitarget_forecast_with_target_specific_feature_set(
#     pipeline_template=template_pipeline,
#     column_ids=[str(id_) for id_ in dataset.summary.column_ids],
#     one_point_backtests=False,
# )
#
# print(results)

## Loop through each target (slower)

results = pipeline_interface.run_multitarget_forecast(
    pipeline_template=template_pipeline,
    column_ids=[str(id_) for id_ in dataset.summary.column_ids],
    one_point_backtests=True,
)
