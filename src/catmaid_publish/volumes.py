from pathlib import Path
from typing import Optional

import meshio
import navis
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
