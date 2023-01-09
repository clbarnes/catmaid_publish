import sys
from typing import Any

import pymaid

from . import __version__
from .constants import DATA_DIR

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def get_data_dir(dname=__version__):
    return DATA_DIR / "output/raw" / dname


def read_toml(fpath):
    with open(fpath, "rb") as f:
        return tomllib.load(f)


def hashable_toml_dict(d: dict[str, Any]):
    out = []
    for k, v in sorted(d.items()):
        if isinstance(v, list):
            v = hashable_toml_list(v)
        elif isinstance(v, dict):
            v = hashable_toml_dict(v)
        out.append((k, v))
    return tuple(out)


def hashable_toml_list(lst: list):
    out = []
    for v in sorted(lst):
        if isinstance(v, list):
            v = hashable_toml_list(v)
        elif isinstance(v, dict):
            v = hashable_toml_dict(v)
        out.append(v)
    return tuple(out)


def hash_toml(fpath) -> str:
    orig = read_toml(fpath)
    hashable = hashable_toml_dict(orig)
    return hex(hash(hashable))[2:]


def get_catmaid_instance(*dicts) -> pymaid.CatmaidInstance:
    kwargs = dict()
    for d in dicts:
        if d:
            kwargs.update(d)
    return pymaid.CatmaidInstance.from_environment(**kwargs)
