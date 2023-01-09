from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

import meshio
import navis
import pandas as pd
import pymaid

from .utils import fill_in_dict


def get_volume_id(vol: navis.Volume):
    """Depends on some implementation details in both navis and trimesh."""
    return vol._kwargs["volume_id"]


def get_volumes(names: Optional[list[str]], rename: dict[str, str]):
    if names is not None:
        names = sorted(set(names).union(rename))

    volumes: dict[str, navis.Volume] = pymaid.get_volume(names)
    rename = fill_in_dict(rename, volumes.keys())

    out = {
        rename[name]: (
            get_volume_id(vol),
            meshio.Mesh(vol.vertices, [("triangle", vol.faces)]),
        )
        for name, vol in volumes.items()
    }

    return out, rename


def write_volumes(dpath: Path, volumes: dict[str, tuple[int, meshio.Mesh]]):
    if not volumes:
        return
    dpath.mkdir(parents=True, exist_ok=True)

    with open(dpath / "names.tsv", "w") as f:
        f.write("filename\tvolume_name\n")
        for name, (vol_id, mesh) in sorted(volumes.items()):
            fname = str(vol_id) + ".stl"
            f.write(f"{fname}\t{name}\n")
            mesh.write(dpath / fname)


def df_to_dict(df: pd.DataFrame, keys, values):
    return dict(zip(df[keys], df[values]))


class VolumeReader:
    def __init__(self, dpath: Path) -> None:
        self.dpath = dpath
        self._names_df = None

    @property
    def names_df(self):
        if self._names_df is None:
            self._names_df = pd.read_csv(
                self.dpath / "names.tsv",
                sep="\t",
            )
        return self._names_df

    @lru_cache
    def _dict(self, keys, values):
        return df_to_dict(self.names_df, keys, values)

    def _read_vol(
        self, fpath: Path, name: Optional[str], volume_id: Optional[int]
    ) -> navis.Volume:
        vol = navis.Volume.from_file(fpath)
        if name is not None:
            d = self._dict("filename", "volume_name")
            name = d[fpath.name]
        vol.name = name

        if volume_id is None:
            volume_id = int(fpath.stem)

        vol.id = volume_id
        return vol

    def get_by_id(self, volume_id: int) -> navis.Volume:
        return self._read_vol(
            self.dpath / f"{volume_id}.stl",
            None,
            volume_id,
        )

    def get_by_name(self, volume_name: str) -> navis.Volume:
        d = self._dict("volume_name", "filename")
        fname = d[volume_name]
        path = self.dpath / fname
        return self._read_vol(path, volume_name, None)

    def get_all(self) -> Iterable[navis.Volume]:
        for fpath in self.dpath.glob("*.stl"):
            yield self._read_vol(fpath, None, None)


README = """
# Volumes

Volumes are regions of interest represented by 3D triangular meshes.

## Files

### `names.tsv`

A tab separated value file with columns
`filename`, `volume_name`.
This maps the name of the volume to the name of the file in which the mesh is stored.

### `*.stl`

Files representing the volume, in ASCII STL format.
""".lstrip()
