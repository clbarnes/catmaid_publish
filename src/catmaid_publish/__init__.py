# isort: skip_file
import sys

from .version import version as __version__  # noqa: F401
from .version import version_tuple as __version_info__  # noqa: F401
from .io_helpers import hash_toml
from .main import publish_from_config
from .reader import (
    DataReader,
    SkeletonReader,
    LandmarkReader,
    VolumeReader,
    AnnotationReader,
)
from .skeletons import ReadSpec
from .landmarks import Location
from .volumes import AnnotatedVolume

if sys.version_info >= (3, 10):
    from importlib.resources import files
else:
    from importlib_resources import files

__doc__ = files("catmaid_publish.package_data").joinpath("README.md").read_text()

__all__ = [
    "publish_from_config",
    "DataReader",
    "hash_toml",
    "ReadSpec",
    "Location",
    "SkeletonReader",
    "LandmarkReader",
    "VolumeReader",
    "AnnotatedVolume",
    "AnnotationReader",
]
