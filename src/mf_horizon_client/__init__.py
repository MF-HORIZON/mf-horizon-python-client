from ._version import get_versions

# pylint: disable-all
_versions_dict = get_versions()
__version__ = _versions_dict["version"]
__gitsha__ = _versions_dict["full-revisionid"]
del get_versions, _versions_dict
