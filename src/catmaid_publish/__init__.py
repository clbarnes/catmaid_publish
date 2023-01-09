"""
# catmaid_publish package
"""
import os

os.environ["NAVIS_HEADLESS"] = "true"
os.environ["NAVIS_SKIP_LOG_SETUP"] = "true"

from .main import publish_from_config
from .version import version as __version__  # noqa: F401
from .version import version_tuple as __version_info__  # noqa: F401

__all__ = ["publish_from_config"]
