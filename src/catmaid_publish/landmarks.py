import pymaid
from typing import Optional

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
    groups: dict[str, list[str]]
    group_locations: dict[str, list[int]]


def get_landmarks(
    groups: list[str],
    group_rename: dict[str, str],
    names: Optional[list[str]],
    rename: dict[str, str],
):
    group_df, group_loc_df, group_members = pymaid.get_landmark_groups(False, True)
    lmark_df, lmark_loc_df = pymaid.get_landmarks()

    if names is None:
        names = list(lmark_df["name"])

    rename = fill_in_dict(rename, names)

    group_id_to_name = dict(group_df[["group_id", "name"]].itertuples(index=False))
    lmark_id_to_name = dict(lmark_df[["landmark_id", "name"]].itertuples(index=False))

    if groups is None:
        groups = list(group_df["name"])

    group_rename = fill_in_dict(group_rename, groups)

    group_members_filtered: dict[str, list[str]] = dict()
    for group_id, lm_ids in group_members.items():
        group_name = group_id_to_name[group_id]
        if group_name not in group_rename:
            continue
        landmarks = [lmark_id_to_name[lm_id] for lm_id in lm_ids]
        fill_in_dict(rename, landmarks, True)
        if landmarks:
            group_members_filtered[group_name] = landmarks

    locations = set()

    locations = dict()
    group_locations = defaultdict(set)
    for row in group_loc_df.itertuples(index=False):
        group_name = group_id_to_name[row.group_id]
        if group_name not in group_rename:
            continue
        locations[row.location_id] = (row.x, row.y, row.z)
        group_locations[group_name].add(row.location_id)
        # todo: skip locs which belong to member landmarks?

    lmark_locations = defaultdict(set)
    for row in lmark_loc_df.itertuples():
        lmark_name = lmark_id_to_name[row.landmark_id]
        if lmark_name not in rename:
            continue
        locations[row.location_id] = (row.x, row.y, row.z)
        lmark_locations[lmark_name].add(row.location_id)

    return LandmarkInfo(
        landmark_locations=dict(sorted(
            (rename[lm], sorted(locs))
            for lm, locs in lmark_locations.items()
        )),
        locations=dict(sorted(locations.items())),
        group_landmarks=group_members_filtered,
        group_locations=dict(sorted(
            (rename[g], sorted(locs))
            for g, locs in group_locations.items()
        )),
    )
