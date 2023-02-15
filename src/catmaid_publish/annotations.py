import json
from pathlib import Path
from typing import Optional

import networkx as nx
import pymaid

from .utils import copy_cache, descendants, fill_in_dict


@copy_cache(maxsize=None)
def annotation_graph() -> nx.DiGraph:
    return pymaid.get_annotation_graph()


def sub_annotations(annotations: list[str], include_roots=True, max_depth=None):
    """Get all descendant annotations of the given annotations.

    Parameters
    ----------
    annotations : list[str]
        Root annotations.
    include_roots : bool, optional
        Whether to include the given roots, by default True.
        If False, will only prune roots which have no parents,
        e.g. a root will be kept if it is annotated by another root.
    max_depth : int, optional
        Maximum depth of descendants, by default None (full depth).

    Returns
    -------
    set[str]
        Set of annotations descended from the given roots.
    """
    g = annotation_graph()
    skels = {n for n, d in g.nodes(data=True) if d.get("is_skeleton")}
    g.remove_nodes_from(skels)

    nodes = descendants(g, annotations, max_depth)
    sub: nx.DiGraph = g.subgraph(nodes).copy()

    if not include_roots:
        to_remove = set()
        for ann in annotations:
            preds = list(sub.predecessors(ann))
            if not preds:
                to_remove.add(ann)

        sub.remove_nodes_from(to_remove)

    return sub


def get_annotations(
    annotated: list[str], names: Optional[list[str]], rename: dict[str, str]
) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Get annotations of interest and how they relate to each other.

    Parameters
    ----------
    annotated : list[str]
        Include all descendant annotations of these meta-annotations.
    names : Optional[list[str]]
        Include annotations with any of these names.
        If None, include all annotations in the project.
    rename : dict[str, str]
        Rename these annotations.

    Returns
    -------
    tuple[dict[str, list[str]], dict[str, str]]
        2-tuple:
        First element is a dict of a (renamed) annotation
        to its (renamed) sub-annotations.
        Second element is the complete dict of renames ``{old: new}``.
    """
    g = annotation_graph()
    skels = {n for n, d in g.nodes(data=True) if d.get("is_skeleton")}
    g.remove_nodes_from(skels)

    if names is None:
        name_set = set(g.nodes)
    else:
        name_set = set(names).union(descendants(g, annotated))

    rename = fill_in_dict(rename, name_set)

    sub = g.subgraph(list(rename))
    out = dict()
    for n in sorted(rename, key=rename.get):
        out[rename[n]] = sorted(rename[s] for s in sub.successors(n))

    return out, rename


def write_annotation_graph(fpath: Path, annotations: dict[str, list[str]]):
    """Write annotation graph as JSON ``{parent: [child1, ...]}``.

    Parameters
    ----------
    fpath : Path
        Path to write to. Ancestor directories will be created.
    annotations : dict[str, list[str]]
        Parent-children annotation relationships.
    """
    fpath.parent.mkdir(exist_ok=True, parents=True)
    with open(fpath, "w") as f:
        json.dump(annotations, f, indent=2, sort_keys=True)


class AnnotationReader:
    """Class for reading exported annotation data."""

    def __init__(self, dpath: Path) -> None:
        """
        Parameters
        ----------
        dpath : Path
            Directory in which the annotation data is saved.
        """
        self.dpath = dpath

    def get_graph(self) -> nx.DiGraph:
        """Return the saved graph of text annotations.

        Returns
        -------
        nx.DiGraph
            Directed graph of text annotations,
            where an edge denotes the source annotating the target.
            All nodes have attributes ``type="annotation``;
            all edges have attributes ``meta_annotation=True``.
        """
        with open(self.dpath / "annotation_graph.json") as f:
            d = json.load(f)

        g = nx.DiGraph()
        for u, vs in d.items():
            for v in vs:
                g.add_edge(u, v, meta_annotation=True)

        for _, d in g.nodes(data=True):
            d["type"] = "annotation"

        return g


README = """
# Annotations

Annotations are text labels applied to neurons and to other annotations.

Data in this directory can be parsed into a `networkx.DiGraph`
using `catmaid_publish.AnnotationReader`.

## Files

### `annotations.json`

A JSON file of annotations and how they annotate each other.
Every annotation of interest is a key in the JSON object:
the value is the list of annotations of interest annotated by that key.
""".lstrip()
