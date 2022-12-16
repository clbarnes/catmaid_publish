from pathlib import Path
from typing import Any, NamedTuple, Optional
import json
from collections import defaultdict

import pandas as pd
import pymaid

from .utils import fill_in_dict


def map_col(col, mapper: dict):
    return [mapper[item] for item in col]


# group_members[group_name, list[lmark_name]]
# group_locations[group_name, list[location_id]]
# landmark_locations[landmark_name, list[location_id]]
# locations[id, x, y, z]
class LandmarkInfo(NamedTuple):
    landmark_locations: dict[str, list[int]]
    locations: dict[int, tuple[float, float, float]]
    group_landmarks: dict[str, list[str]]
    group_locations: dict[str, list[int]]

    def is_empty(self):
        return all(len(item) == 0 for item in self)


class LocationSet:
    def __init__(self) -> None:
        self.data = dict()


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


def write_landmarks(fpath: Path, landmarks: pd.DataFrame, groups: pd.DataFrame):
    if len(landmarks) + len(groups) == 0:
        return

    location_data = dict()
    for row in landmarks.itertuples(index=False):
        d = location_data.setdefault(
            row.location_id,
            {
                "xyz": [row.x, row.y, row.z],
                "groups": set(),
                "landmarks": set(),
            },
        )
        d["landmarks"].add(row.name)

    for row in groups.itertuples(index=False):
        d = location_data.setdefault(
            row.location_id,
            {
                "xyz": [row.x, row.y, row.z],
                "groups": set(),
                "landmarks": set(),
            },
        )
        d["groups"].add(row.name)

    out = []
    for _, v in sorted(location_data.items()):
        v["landmarks"] = sorted(v["landmarks"])
        v["groups"] = sorted(v["groups"])
        out.append(v)

    with open(fpath, "w") as f:
        json.dump(location_data, f, indent=2, sort_keys=True)


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
