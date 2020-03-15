import os

import versioneer
from setuptools import find_namespace_packages, setup

install_requires = [
    "numpy",
    "pandas",
    "urllib3",
    "requests",
    "dataclasses",
    "marshmallow",
    "marshmallow-enum",
    "tqdm",
    "marshmallow-oneofschema",
]

docs_extras = [
    "ipykernel",
    "jupyter",
    "matplotlib",
    "pillow",
    "sphinx",
    "sphinx-gallery",
]
dev_extras = [
    "black",
    "check-manifest",
    "coverage",
    "mypy",
    "isort",
    "pre-commit",
    "pylint",
    "pytest",
    "tox",
]

extras_require = {"dev": dev_extras, "docs": docs_extras}


# Add a `pip install .[all]` target:
all_extras = set()
for extras_list in extras_require.values():
    all_extras.update(extras_list)
extras_require["all"] = list(all_extras)

version = versioneer.get_version()

project_repo_dir = os.path.abspath(os.path.dirname(__file__))

# Get the long description from the README file
with open(os.path.join(project_repo_dir, "README.rst"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="mf_horizon_client",
    version=version,
    cmdclass=versioneer.get_cmdclass(),
    description="Lightweight Python wrapper for Mind Foundry Horizon API",
    long_description=long_description,
    # The project"s main homepage.
    url="https://mindfoundry.ai",
    # Author details
    author="Mind Foundry Ltd",
    author_email="dev@mindfoundry.ai",
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # Finally, add an invalid classifier, as a failsafe against uploading to PyPI.
        "Private :: Do Not Upload"
    ],
    packages=find_namespace_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=install_requires,
    extras_require=extras_require,
)
