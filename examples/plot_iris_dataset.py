"""
A Packaged Data Example
==================================================

This example loads a dataset that was included with the Python package.
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pkg_resources

###########################################################
# When loading a dataset, it's good practice to use the 'pkg_resources' API,
# cf https://setuptools.readthedocs.io/en/latest/setuptools.html#accessing-data-files-at-runtime
iris_datapath = pkg_resources.resource_filename(
    "mf_horizon_client", "datasets/iris/iris.csv"
)

###########################################################
iris_df = pd.read_csv(iris_datapath)
###########################################################
# Let's look at the axis-projections of the iris dataset:
ax = plt.gca()
for species_name, subgroup_df in iris_df.groupby(iris_df["class"]):
    ax.scatter(
        "sepallength", "sepalwidth", data=subgroup_df, label=species_name, alpha=0.7
    )
ax.legend()
ax.set_title("A Matplotlib scatterplot")
