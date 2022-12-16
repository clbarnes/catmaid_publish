import json
from typing import Any, Optional
from collections.abc import Iterable
from collections import defaultdict
from pathlib import Path

import pymaid
from tqdm import tqdm
import pandas as pd
import numpy as np

from .utils import fill_in_dict


def get_all_skids():
    try:
        # once https://github.com/navis-org/pymaid/pull/227 is released
        return pymaid.get_skeleton_ids()
    except ImportError:
        pass

    cm = pymaid.utils._eval_remote_instance(None)
    url = cm.make_url(
        cm.project_id,
        "skeletons",
    )
    return set(cm.fetch(url))


def filter_tags(
    tags: dict[str, list[int]], names: Optional[list[str]], rename: dict[str, str]
):
    if names is None:
        rename = fill_in_dict(rename, list(tags))
    else:
        rename = fill_in_dict(rename, names)

    return {rename[k]: sorted(v) for k, v in tags.items() if k in rename}


def get_renamed_annotations(
    nrn: pymaid.CatmaidNeuron, rename: dict[str, str]
) -> set[str]:
    anns = nrn.get_annotations()
    return {rename[a] for a in anns if a in rename}


def get_skeletons(
    annotated: list[str],
    names: Optional[list[str]],
    rename: dict[str, str],
    tag_names: Optional[list[str]],
    tag_rename: dict[str, str],
    annotations_rename: dict[str, str],
) -> Iterable[tuple[pymaid.CatmaidNeuron, dict[str, Any]]]:
    if names is None:
        skids = get_all_skids()
    else:
        skids = set()
        if names:
            skids.update(pymaid.get_skids_by_name(names))
        if rename:
            skids.update(pymaid.get_skids_by_name(list(rename)))
        if annotated:
            skids.update(pymaid.get_skids_by_annotation(annotated))

    for skid in tqdm(sorted(skids), desc="Skeletons"):
        nrn: pymaid.CatmaidNeuron = pymaid.get_neuron(skid)
        nrn.name = rename.get(nrn.name, nrn.name)
        nrn.tags = filter_tags(nrn.tags, tag_names, tag_rename)
        anns = get_renamed_annotations(nrn, annotations_rename)
        meta = {
            "name": fn_or_none(nrn.name, str),
            "id": int(nrn.id),
            "soma_id": fn_or_none(nrn.soma, int),
            "annotations": sorted(anns),
        }
        yield nrn, meta


def fn_or_none(item, fn):
    if item is None:
        return None
    return fn(item)


def sort_skel_dfs(df: pd.DataFrame, roots, sort_children=True, inplace=False):
    """Depth-first search tree to ensure parents are always defined before children."""
    children = defaultdict(list)
    node_id_to_orig_idx = dict()
    for row in df.itertuples():
        child = row.node_id
        parent = row.parent_id
        children[parent].append(child)
        node_id_to_orig_idx[child] = row.Index

    if sort_children:
        to_visit = sorted(roots, reverse=True)
    else:
        to_visit = list(roots)[::-1]

    order = np.full(len(df), np.nan)
    count = 0
    while to_visit:
        node_id = to_visit.pop()
        order[node_id_to_orig_idx[node_id]] = count
        cs = children.pop(order[-1], [])
        if sort_children:
            to_visit.extend(sorted(cs, reverse=True))
        else:
            to_visit.extend(cs[::-1])
        count += 1

    # undefined behaviour if any nodes are not reachable from the given roots

    if not inplace:
        df = df.copy()

    df["_order"] = order
    df.sort_values("_order", inplace=True)
    df.drop(columns=["_order"], inplace=True)
    return df


def write_skeleton(dpath: Path, nrn: pymaid.CatmaidNeuron, meta: dict[str, Any]):
    dpath.mkdir(parents=True)

    with open(dpath / "metadata.json", "w") as f:
        json.dump(meta, f, indent=2, sort_keys=True)

    with open(dpath / "tags.json", "w") as f:
        json.dump(nrn.tags, f, sort_keys=True, indent=2)

    nodes = sort_skel_dfs(
        nrn.nodes[["node_id", "parent_id", "x", "y", "z", "radius"]],
        nrn.root,
    )
    nodes.to_csv(dpath / "nodes.tsv", sep="\t", index=False)

    conns = nrn.connectors.sort_values("node_id", inplace=False)
    conns.rename(columns={"type": "is_input"}, inplace=True)
    conns.to_csv(dpath / "connectors.tsv", sep="\t", index=False)


README = """
# Neurons

Each neuron is represented by a directory whose name is an arbitrary integer ID associated with the neuron.
A neuron is represented by a skeleton:
a tree graph of points in 3D space ("nodes") which each have an integer ID.
Neurons also have tags: text labels applied to certain nodes.
Synapses between neurons are represented as connectors:
a point in 3D space associated with a node, which may be an input or an output.
Finally, neurons have some associated metadata, including their name, a set of annotations (text labels associated with the neuron rather than its nodes), and optionally the node ID of the neuron's soma.

## Files

### `*/nodes.tsv`

A tab separated value file with columns
`node_id` (int), `parent_id` (int), `x`, `y`, `z`, `radius` (all decimal).

A `parent_id` of `-1` indicates that the node does not have a parent, i.e. is the root.
Otherwise, `parent_id` refers to the `node_id` of the node's parent.
A `radius` of `-1.0` indicates that the radius of the neuron at this location has not been measured.

Nodes are sorted topologically so that a node's parent is guaranteed to appear before it in the table.

### `*/tags.json

A JSON file mapping tags (text labels) to the set of nodes (as integer IDs) to which they are applied.

### `*/connectors.tsv`

A tab separated value file with columns
`node_id` (int), `connector_id` (int), `is_input` (boolean as `0`/`1`), `x`, `y`, `z` (all decimal).
The `node_id` refers to rows of `nodes.tsv`.
`connector_id` is consistent among other neurons in this dataset (although not necessarily with other datasets).
`is_input` represents whether the synapse is an output/ presynapse (`0`) or input/ postsynapse (`1`).

By comparing the `connector_id` and `is_input` of `connectors.tsv` files between neurons, you can determine synaptic partners.
However, not all partners are guaranteed to be in this dataset.

### `*/metadata.json`

A JSON file with miscellaneous data about the neuron, including:

- `"name"`: name of the neuron
- `"id"`: integer ID of the neuron
- `"soma_id"`: integer ID of the neuron's soma (`null` if not labeled)
- `"annotations"`: listi of string labels applied to the neuron
""".lstrip()
