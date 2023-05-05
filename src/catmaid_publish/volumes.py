import json
from collections import defaultdict
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional, Union

import meshio
import navis
import networkx as nx
import numpy as np
import pandas as pd
import pymaid

from catmaid_publish.constants import CACHE_SIZE

from .utils import copy_cache, descendants, entity_graph, fill_in_dict


class AnnotatedVolume(navis.Volume):
    def __init__(
        self,
        vertices: Union[list, np.ndarray],
        faces: Union[list, np.ndarray] = None,
        name: Optional[str] = None,
        color: Union[str, Sequence[Union[int, float]]] = (0.85, 0.85, 0.85, 0.2),
        id: Optional[int] = None,
        annotations: Optional[set[str]] = None,
        **kwargs,
    ):
        super().__init__(vertices, faces, name, color, id, **kwargs)
        self.annotations = set() if not annotations else set(annotations)


def get_volume_id(vol: navis.Volume):
    """Depends on some implementation details in both navis and trimesh."""
    return vol._kwargs["volume_id"]


def get_volumes(
    annotated: list[str],
    names: Optional[list[str]],
    rename: dict[str, str],
    ann_renames: dict[str, str],
) -> tuple[dict[str, tuple[int, meshio.Mesh, set[str]]], dict[str, str]]:
    """
    Returns 2-tuple:

    (
        {vol_renamed: (vol_id, mesh, renamed_annotations)},
        {orig_name: out_name}
    )
    """

    name_to_anns = defaultdict(set)
    g = entity_graph()
    for v, d in g.nodes(data=True):
        if d["type"] != "volume":
            continue
        for parent in g.predecessors(v):
            parent_d = g.nodes[parent]
            if parent_d["type"] != "annotation":
                continue
            name_to_anns[d["name"]].add(parent_d["name"])

    if names is not None:
        name_set = set(rename)

        if annotated:
            ann_set = set(annotated)
            roots = [
                d["id"]
                for _, d in g.nodes(data=True)
                if d["type"] == "annotation" and d["name"] in ann_set
            ]
            for vol_id in descendants(
                g, roots, select_fn=lambda _, d: d["type"] == "volume"
            ):
                name_set.add(g.nodes[vol_id]["name"])

        name_set.update(names)
        names = sorted(name_set)

    volumes: dict[str, navis.Volume] = pymaid.get_volume(names)
    rename = fill_in_dict(rename, volumes.keys())

    out = {
        rename[name]: (
            get_volume_id(vol),
            meshio.Mesh(vol.vertices, [("triangle", vol.faces)]),
            {ann_renames[a] for a in name_to_anns[name] if a in ann_renames},
        )
        for name, vol in volumes.items()
    }

    return out, rename


def write_volumes(dpath: Path, volumes: dict[str, tuple[int, meshio.Mesh, set[str]]]):
    if not volumes:
        return
    dpath.mkdir(parents=True, exist_ok=True)

    ann_data = defaultdict(set)

    with open(dpath / "names.tsv", "w") as f:
        f.write("filename\tvolume_name\n")
        for name, (vol_id, mesh, anns) in sorted(volumes.items()):
            fname = str(vol_id) + ".stl"
            f.write(f"{fname}\t{name}\n")
            mesh.write(dpath / fname)
            for ann in anns:
                ann_data[ann].add(name)

    with open(dpath / "annotations.json", "w") as f:
        json.dump({k: sorted(v) for k, v in ann_data.items()}, f)


def df_to_dict(df: pd.DataFrame, keys, values):
    return dict(zip(df[keys], df[values]))


class VolumeReader:
    """Class for reading exported volume data."""

    def __init__(self, dpath: Path) -> None:
        """
        Parameters
        ----------
        dpath : Path
            Path to directory in which the volume data is saved.
        """
        self.dpath = dpath
        self._names_df = None

    @property
    def names_df(self) -> pd.DataFrame:
        """Dataframe representing ``names.tsv``.

        Returns
        -------
        pd.DataFrame
            Columns ``filename``, ``volume_name``
        """
        if self._names_df is None:
            self._names_df = pd.read_csv(
                self.dpath / "names.tsv",
                sep="\t",
            )
        return self._names_df

    @lru_cache
    def _dict(self, keys, values):
        return df_to_dict(self.names_df, keys, values)

    @copy_cache(maxsize=None)
    def _get_annotations(self) -> dict[str, set[str]]:
        """Map annotation names to volume names.

        Returns
        -------
        dict[str, set[str]]
        """
        d = json.loads((self.dpath / "annotations.json").read_text())
        return {k: set(v) for k, v in d.items()}

    def get_annotation_graph(self) -> nx.DiGraph:
        """Get graph of annotations to volumes.

        Returns
        -------
        networkx.DiGraph
        """
        g = nx.DiGraph()
        for k, vs in self._get_annotations().items():
            g.add_node(k, type="annotation")
            for v in vs:
                if v not in g.nodes:
                    g.add_node(v, type="volume")
                g.add_edge(k, v, meta_annotation=False)
        return g

    def _annotations_for_volume(self, name: str):
        d = self._get_annotations()
        return {a for a, names in d.items() if name in names}

    @copy_cache(maxsize=CACHE_SIZE)
    def _read_vol(
        self, fpath: Path, name: Optional[str], volume_id: Optional[int]
    ) -> AnnotatedVolume:
        vol = AnnotatedVolume.from_file(fpath)
        if name is not None:
            d = self._dict("filename", "volume_name")
            name = d[fpath.name]
        vol.name = name

        vol.annotations.update(self._annotations_for_volume(name))

        if volume_id is None:
            volume_id = int(fpath.stem)

        vol.id = volume_id
        return vol

    def get_by_id(self, volume_id: int) -> AnnotatedVolume:
        """Read a volume with a given (arbitrary) ID.

        Parameters
        ----------
        volume_id : int

        Returns
        -------
        AnnotatedVolume
        """
        return self._read_vol(
            self.dpath / f"{volume_id}.stl",
            None,
            volume_id,
        )

    def get_by_name(self, volume_name: str) -> AnnotatedVolume:
        """Read a volume with a given name.

        Parameters
        ----------
        volume_name : str

        Returns
        -------
        AnnotatedVolume
        """
        d = self._dict("volume_name", "filename")
        fname = d[volume_name]
        path = self.dpath / fname
        return self._read_vol(path, volume_name, None)

    def get_by_annotation(self, annotation: str) -> Iterable[AnnotatedVolume]:
        """Lazily iterate through all volumes with the given annotation.

        Parameters
        ----------
        annotation : str
            Annotation name.

        Yields
        ------
        Iterable[AnnotatedVolume]
        """
        d = self._get_annotations()
        for vol_name in d[annotation]:
            yield self.get_by_name(vol_name)

    def get_all(self) -> Iterable[AnnotatedVolume]:
        """Lazily iterate through all available volumes.

        Iteration is in the order used by ``names.tsv``.

        Yields
        ------
        AnnotatedVolume
        """
        for fname, name in self._dict("filename", "volume_name").items():
            fpath = self.dpath / fname
            yield self._read_vol(fpath, name, None)


README = """
# Volumes

Volumes are regions of interest represented by 3D triangular meshes.

Data in this directory can be parsed into `AnnotatedVolume`s
(a subclass of `navis.Volume` which simply adds an attribute `annotations: set[str]`)
using `catmaid_publish.VolumeReader`.

## Files

### `names.tsv`

A tab separated value file with columns
`filename`, `volume_name`.
This maps the name of the volume to the name of the file in which the mesh is stored.

### `*.stl`

Files representing the volume, in ASCII STL format, named with an arbitrary ID.

### `annotations.json`

A JSON file mapping annotation names to an array of the names of volumes it annotates.
""".lstrip()
