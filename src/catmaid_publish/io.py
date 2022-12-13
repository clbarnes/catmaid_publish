from . import __version__
from .constants import DATA_DIR

try:
    import tomllib
except ImportError:
    import tomli as tomllib


def get_data_dir(dname=__version__):
    return DATA_DIR / "output/raw" / version


def read_toml(fpath):
    with open(fpath) as f:
        return tomllib.load(f)
