import json
from pathlib import Path
from typing import Optional

import networkx as nx
import pymaid

from .utils import fill_in_dict


def descendants(g: nx.DiGraph, roots: list[str], max_depth=None):
    """Find all descendant nodes from given roots, to a given depth."""
    out = set()
    to_visit: list[tuple[str, int]] = [(r, 0) for r in roots]
    while to_visit:
        node, depth = to_visit.pop()
        if node in out:
            continue
        out.add(node)
        if max_depth is not None and depth >= max_depth:
            continue
        to_visit.extend((n, depth + 1) for n in g.successors(node))
    return out


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
    g = pymaid.get_annotation_graph()
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
    """Write annotation graph as JSON ``{parent: children}``.

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


def read_annotation_graph(fpath):
    with open(fpath) as f:
        d = json.load(f)

    g = nx.DiGraph()
    for u, vs in d.items():
        for v in vs:
            g.add_edge(u, v)

    return g


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

## Files

### `annotations.json`

A JSON file of annotations and how they annotate each other.
Every annotation of interest is a key in the JSON object:
the value is the list of annotations of interest annotated by that key.
""".lstrip()
