from typing import Optional
import pymaid
import networkx as nx

from .utils import fill_in_dict


def descendants(g: nx.DiGraph, roots: list[str]):
    out = set()
    to_visit = list(roots)
    while to_visit:
        n = to_visit.pop()
        if n in out:
            continue
        out.add(n)
        to_visit.extend(g.successors(n))
    return out


def get_annotations(annotated: list[str], names: Optional[list[str]], rename: dict[str, str]) -> tuple[list[tuple[str, list[str]]], dict[str, str]]:
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
        out[rename[n]] = sorted(rename[s] for s in g.successors(n))

    return out, rename
