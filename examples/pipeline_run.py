import pandas as pd
from mf_horizon_client.client.horizon_client import HorizonClient
from mf_horizon_client.client.pipelines.blueprints import BlueprintType

URL = "https:// <<MY HORIZON URL >>"
API_KEY = "<< MY API KEY >>"

client = HorizonClient(server_url=URL, api_key=API_KEY, max_retries=1,)

data_interface = client.data_interface()
pipeline_interface = client.pipeline_interface()

df = pd.read_csv("tech_stocks.csv").dropna()

dataset = data_interface.upload_data(data=df, name="Tech Stocks")

pipeline = pipeline_interface.create_pipeline(
    dataset_id=dataset.summary.id_, name="Test Pipeline", blueprint=BlueprintType.fast_forecasting,
)

pipeline_interface.directional_response_regression(

)
