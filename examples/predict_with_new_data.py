from typing import cast

import numpy as np
import pandas as pd

from examples.credentials import URL, API_KEY
from mf_horizon_client.data_structures.configs.stage_config import ProblemSpecificationConfig

from mf_horizon_client.client.pipelines.blueprints import BlueprintType

from mf_horizon_client.client.horizon_client import HorizonClient

client = HorizonClient(server_url=URL, api_key=API_KEY, max_retries=1, )

pipeline_interface = client.pipeline_interface()
data_interface = client.data_interface()

df = pd.DataFrame(pd.date_range("2000", "2002"))

for c in "AB":
    df[c] = np.random.randn(len(df))

train_data = df.iloc[:200]
test_data = df[200:]

dataset = data_interface.upload_data(data=train_data, name="Train Data Predict Example")

pipeline = pipeline_interface.create_pipeline(
    dataset_id=dataset.summary.id_, blueprint=BlueprintType.fast_forecasting, name="ST"
)

cast(ProblemSpecificationConfig, pipeline.stages[0].config).horizons = [1]

pipeline_interface.update_config(
    pipeline_id=pipeline.summary.id_,
    stage_id=pipeline.stages[0].id_,
    config=pipeline.stages[0].config
)

pipeline_interface.run_pipeline(pipeline.summary.id_, synchronous=True)
predictions = pipeline_interface.fit_predict(pipeline_id=pipeline.summary.id_, data=test_data)
