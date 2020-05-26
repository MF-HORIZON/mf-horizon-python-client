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
    "scikit-learn",
    "marshmallow-oneofschema",
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

extras_require = {"dev": dev_extras}


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
    download_url='https://github.com/MF-HORIZON/mf-horizon-python-client/archive/v2.2.2.tar.gz',
    # The project"s main homepage.
    url="https://www.mindfoundry.ai/horizon",
    # Author details
    author="Mind Foundry Ltd",
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
    ],
    author_email="stanley.speel@mindfoundry.ai",
    packages=find_namespace_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=install_requires,
    extras_require=extras_require,
)
