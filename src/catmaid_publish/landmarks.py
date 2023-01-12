from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Optional

import pandas as pd
import pymaid

from .utils import fill_in_dict


def get_landmarks(
    groups: Optional[list[str]],
    group_rename: dict[str, str],
    names: Optional[list[str]],
    rename: dict[str, str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Get locations associated with landmarks and groups.

    Parameters
    ----------
    groups : Optional[list[str]]
        List of group names of interest (None means all)
    group_rename : dict[str, str]
        Remap group names.
    names : Optional[list[str]]
        List of landmark names of interest(None means all)
    rename : dict[str, str]
        Remap landmark names.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        Dataframes have columns location_id, x, y, z, name.

        The first element refers to landmarks, the second to groups.
        Locations are not unique as they can belong to several landmarks and/or groups.
    """
    lmark_df, lmark_loc_df = pymaid.get_landmarks()

    if names is None:
        names = list(lmark_df["name"])
    rename = fill_in_dict(rename, names)

    # location_id, x, y, z, landmark_id
    # landmark_id, name, user_id, project_id, creation_time, edition_time
    lmark_combined = lmark_loc_df.merge(lmark_df, on="landmark_id")
    lmark_reduced = lmark_combined.loc[lmark_combined["name"].isin(rename)].copy()
    lmark_reduced["name"] = [rename[old] for old in lmark_reduced["name"]]
    lmark_final = lmark_reduced.drop(
        columns=[
            "landmark_id",
            "user_id",
            "project_id",
            "creation_time",
            "edition_time",
        ],
        inplace=False,
    )

    group_df, group_loc_df, _ = pymaid.get_landmark_groups(True, False)

    if groups is None:
        groups = list(group_df["name"])
    group_rename = fill_in_dict(group_rename, groups)

    # location_id, x, y, z, group_id
    # group_id, name, user_id, project_id, creation_time, edition_time.
    group_combined = group_loc_df.merge(group_df, on="group_id")
    group_reduced = group_combined.loc[group_combined["name"].isin(group_rename)].copy()
    group_reduced["name"] = [group_rename[old] for old in group_reduced["name"]]

    group_final = group_reduced.drop(
        columns=["group_id", "user_id", "project_id", "creation_time", "edition_time"],
        inplace=False,
    )

    return lmark_final, group_final


@dataclass
class Location:
    """Location of importants to landmarks and groups.

    Attributes
    ----------
    xyz : tuple[float, float, float]
        Coordinates of location
    groups : set[str]
        Set of landmark groups this location belongs to.
    landmarks : set[str]
        Set of landmarks this location belongs to.
    """

    xyz: tuple[float, float, float]
    groups: set[str] = field(default_factory=set)
    landmarks: set[str] = field(default_factory=set)

    def to_jso(self) -> dict[str, Any]:
        """Convert to JSON-serialisable object.

        Returns
        -------
        dict[str, Any]
        """
        d = asdict(self)
        d["xyz"] = list(d["xyz"])
        d["groups"] = sorted(d["groups"])
        d["landmarks"] = sorted(d["landmarks"])
        return d

    @classmethod
    def from_jso(cls, jso: dict[str, Any]) -> Location:
        """Instantiate from JSON-like dict.

        Parameters
        ----------
        jso : dict[str, Any]
            Keys ``"xyz"`` (3-length list of float),
            ``"groups"`` (list of str),
            ``"landmarks"`` (list of str)

        Returns
        -------
        Location
        """
        return cls(
            tuple(jso["xyz"]),
            set(jso["groups"]),
            set(jso["landmarks"]),
        )


def write_landmarks(fpath: Path, landmarks: pd.DataFrame, groups: pd.DataFrame):
    if len(landmarks) + len(groups) == 0:
        return

    location_data: dict[int, Location] = dict()
    for row in landmarks.itertuples(index=False):
        d = location_data.setdefault(row.location_id, Location((row.x, row.y, row.z)))
        d.landmarks.add(row.name)

    for row in groups.itertuples(index=False):
        d = location_data.setdefault(row.location_id, Location((row.x, row.y, row.z)))
        d.groups.add(row.name)

    out = [v.to_jso() for _, v in sorted(location_data.items())]

    with open(fpath, "w") as f:
        json.dump(out, f, indent=2, sort_keys=True)


class LandmarkReader:
    """Class for reading exported landmark data."""

    def __init__(self, dpath: Path) -> None:
        """
        Parameters
        ----------
        dpath : Path
            Directory in which landmark data is saved.
        """
        self.dpath = dpath
        self.fpath = dpath / "locations.json"

    @lru_cache
    def _locations(self):
        with open(self.fpath) as f:
            d = json.load(f)

        return [Location.from_jso(loc) for loc in d]

    def get_all(self) -> Iterable[Location]:
        """Lazily iterate through landmark locations.

        Yields
        ------
        Location
        """
        yield from self._locations()

    def get_group_names(self) -> set[str]:
        """Return all groups with locations in the dataset.

        Returns
        -------
        set[str]
            Set of group names.
        """
        out = set()
        for loc in self._locations():
            out.update(loc.groups)
        return out

    def get_landmark_names(self) -> set[str]:
        """Return all landmarks with locations in the dataset.

        Returns
        -------
        set[str]
            Set of landmark names.
        """
        out = set()
        for loc in self._locations():
            out.update(loc.landmarks)
        return out

    def get_group(self, *group: str) -> Iterable[Location]:
        """Lazily iterate through all locations from any of the given groups.

        Parameters
        ----------
        group : str
            Group name (can give multiple as *args).

        Yields
        ------
        Location
        """
        groupset = set(group)
        for loc in self._locations():
            if not loc.groups.isdisjoint(groupset):
                yield loc

    def get_landmark(self, *landmark: str) -> Iterable[Location]:
        """Lazily iterate through all locations from any of the given landmarks.

        Parameters
        ----------
        landmark : str
            Landmark name (can give multiple as *args)
        """
        lmarkset = set(landmark)
        for loc in self._locations():
            if not loc.landmarks.isdisjoint(lmarkset):
                yield loc


README = """
# Landmarks

Landmarks represent important points in space.
A *landmark* can have multiple *locations* associated with it:
for example, one landmark can represent a neuron lineage entry point which exists on both sides of the central nervous system, or is segmentally repeated.

A landmark *group* is a collection of *landmark*s.
For example, a landmark group can represent all neuron lineage entry points in the brain.
However, not all of a *landmark*'s *location*s are necessarily associated with a *group* even if the group includes that *landmark*.
This allows for *landmark*/ *group* intersections like:

- landmark: bilateral pair of homologous neuron lineage **A** entry points
- group: all neuron lineage entry points on the **left** side of the brain

## Files

### `locations.json`

A JSON file which is an array of objects representing locations of interest.

Each object's keys are:

- `"landmarks"`: array of names of landmarks to which this location belongs
- `"groups"`: array of names of landmark groups to which this location belongs
- `"xyz"`: 3-length array of decimals representing coordinates of location
""".lstrip()
