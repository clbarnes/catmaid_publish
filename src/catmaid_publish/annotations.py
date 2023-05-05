import json
from pathlib import Path
from typing import Optional

import networkx as nx

from .utils import copy_cache, descendants, entity_graph, fill_in_dict, remove_nodes


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
    g = entity_graph()
    remove_nodes(g, lambda _, d: d["type"] != "annotation")

    if names is None:
        name_set = set(g.nodes)
    else:
        ann_set = set(annotated)
        roots = [d["id"] for _, d in g.nodes(data=True) if d["name"] in ann_set]
        desc = descendants(g, roots)
        name_set = set(names).union(g.nodes[d]["name"] for d in desc)

    rename = fill_in_dict(rename, name_set)

    sub = g.subgraph((n for n, d in g.nodes(data=True) if d["name"] in rename))
    id_to_name = {n: d["name"] for n, d in sub.nodes(data=True) if d["name"] in rename}
    out = dict()
    for n in sorted(id_to_name, key=id_to_name.get):
        out[id_to_name[n]] = sorted(
            rename[sub.nodes[s]["name"]] for s in sub.successors(n)
        )

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

    @copy_cache()
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
