import sys
from collections.abc import Mapping
from typing import Any, Optional

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


NO_DEFAULT = object()


class Config:
    def __init__(self, d: Optional[dict[str, Any]] = None) -> None:
        if d is None:
            d = dict()
        self._d = d

    def get(self, *keys, default=NO_DEFAULT, as_config=True) -> Any:
        """Default only applies to final key."""
        d = self._d
        for idx, k in enumerate(keys, 1):
            try:
                d = d[k]
            except KeyError as e:
                if idx == len(keys) and default is not NO_DEFAULT:
                    return default
                raise e

        if as_config and isinstance(d, Mapping):
            return type(self)(d)

        return d

    @classmethod
    def from_toml(cls, path):
        with open(path, "rb") as f:
            d = tomllib.load(f)
        return cls(d)

    def __hash__(self):
        hashable = hashable_toml_dict(self._d)
        return hash(hashable)

    def hex_digest(self):
        return hex(hash(self)).split("x")[1]


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
