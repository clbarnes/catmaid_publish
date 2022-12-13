import logging
from collections.abc import Iterable

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
