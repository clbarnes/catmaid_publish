import sys
from pathlib import Path
from typing import Any

import pymaid

from . import __version__
from .annotations import AnnotationReader
from .constants import DATA_DIR
from .landmarks import LandmarkReader
from .skeletons import SkeletonReader
from .volumes import VolumeReader

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


class DataReader:
    def __init__(self, dpath: Path) -> None:
        self.dpath = dpath

        self.volumes = (
            VolumeReader(dpath / "volumes") if (dpath / "volumes").is_dir() else None
        )
        self.landmarks = (
            LandmarkReader(dpath / "landmarks")
            if (dpath / "landmarks").is_dir()
            else None
        )
        self.neurons = (
            SkeletonReader(dpath / "neurons") if (dpath / "neurons").is_dir() else None
        )
        self.annotations = (
            AnnotationReader(dpath / "annotations")
            if (dpath / "annotations").is_dir()
            else None
        )
