import logging
from collections.abc import Iterable
from copy import copy, deepcopy
from functools import lru_cache, wraps
from typing import Optional, TypeVar

import networkx as nx

logger = logging.getLogger(__name__)


def setup_logging(level=logging.DEBUG):
    """Sane default logging setup.

    Should only be called once, and only by a script.
    """
    logging.basicConfig(level=level)

    # these are packages with particularly noisy logging
    logging.getLogger("urllib3").setLevel(logging.INFO)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)


T = TypeVar("T")


def fill_in_dict(to_fill: dict[T, T], fill_with: Iterable[T], inplace=False):
    if not inplace:
        to_fill = dict(to_fill)

    for f in fill_with:
        if f not in to_fill:
            to_fill[f] = f

    return to_fill


def copy_cache(deep: bool = True, maxsize: Optional[int] = 128, typed: bool = False):
    """Decorator factory wrapping functools.lru_cache, which copies return values.

    Use this for functions with mutable return values.
    N.B. must be called with parentheses.

    Parameters
    ----------
    deep : bool, optional
        Whether to deepcopy return values, by default True
    maxsize : Optional[int], optional
        See lru_cache, by default 128.
        Use None for an unbounded cache (which is also faster).
    typed : bool, optional
        See lru_cache, by default False

    Returns
    -------
    Callable[[Callable], Callable]
        Returns a decorator.

    Examples
    --------
    >>> @copy_cache()  # must include parentheses, unlike some zero-arg decorators
    ... def my_function(key: str, value: int) -> dict:
    ...     return {key: value}
    ...
    >>> d1 = my_function("a", 1)
    >>> d1["b"] = 2
    >>> d2 = my_function("a", 1)
    >>> "b" in d2  # would be True with raw functools.lru_cache
    False
    """
    copier = deepcopy if deep else copy

    def wrapper(fn):
        wrapped = lru_cache(maxsize, typed)(fn)

        @wraps(fn)
        def copy_wrapped(*args, **kwargs):
            out = wrapped(*args, **kwargs)
            return copier(out)

        copy_wrapped.cache_info = wrapped.cache_info
        copy_wrapped.cache_clear = wrapped.cache_clear

        return copy_wrapped

    return wrapper


def descendants(g: nx.DiGraph, roots: list[str], max_depth=None) -> set[str]:
    """Find all descendant nodes from given roots, to a given depth.

    Output includes given roots.
    """
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


def join_markdown(*strings: Optional[str]) -> str:
    """Join stripped markdown strings with thematic breaks.

    Returns
    -------
    str
    """
    out = []
    for s in strings:
        if s is None:
            continue
        s = s.strip()
        if s:
            out.append(s)

    if out:
        out.append(out.pop() + "\n")

    return "\n\n---\n\n".join(out)
