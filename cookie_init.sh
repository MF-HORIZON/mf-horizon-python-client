#!/bin/bash



set -e
git init
git add .
pip install black isort
echo "Running autoformatters to tidy up any templating issues..."
echo "Running black:"
black -v .
echo "Running isort:"
isort -y
git commit -am "Initial template commit"
python versioneer.py setup
# Versioneer messes up the root '__init__.py', revert it:
git checkout -f HEAD -- src/mf_horizon_client/__init__.py
git commit -m "Initialize versioneer"
pip install -e .[all]
# Install hooks after versioneer setup to avoid reformatting versioneer.py:
pre-commit install


