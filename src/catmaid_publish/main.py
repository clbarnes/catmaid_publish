"""
Export data from CATMAID in plaintext formats with simple configuration.
"""
import datetime as dt
import logging
from argparse import ArgumentParser
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import tomli_w
from tqdm import tqdm

from . import __version__
from .annotations import README as ann_readme
from .annotations import get_annotations, write_annotation_graph
from .constants import README_FOOTER_KEY
from .io_helpers import Config, get_catmaid_instance, read_toml
from .landmarks import README as lmark_readme
from .landmarks import get_landmarks, write_landmarks
from .skeletons import README as skel_readme
from .skeletons import get_skeletons, write_skeleton
from .utils import join_markdown, setup_logging
from .volumes import README as vol_readme
from .volumes import get_volumes, write_volumes


def all_or_names(c: Config) -> Optional[list[str]]:
    """If 'all' key is true, return None, else return 'names' value."""
    if c.get("all", default=False):
        return None
    return c.get("names", default=[])


def publish_annotations(config: Config, out_dir: Path, pbar=None):
    if pbar is not None:
        pbar.set_description("Fetching annotations")

    ann_conf = config.get("annotations", default=Config())
    ann_children, ann_renames = get_annotations(
        ann_conf.get("annotated", default=[]),
        all_or_names(ann_conf),
        ann_conf.get("rename", default=dict()),
    )
    if ann_children:
        if pbar is not None:
            pbar.set_description("Writing annotations")
        (out_dir / "annotations").mkdir()
        readme = join_markdown(
            ann_readme,
            ann_conf.get(README_FOOTER_KEY, default=""),
        )
        (out_dir / "annotations/README.md").write_text(readme)
        write_annotation_graph(
            out_dir / "annotations/annotation_graph.json", ann_children
        )
        ret = True
    else:
        ret = False

    if pbar is not None:
        pbar.update(1)

    return ret, ann_renames


def publish_skeletons(config: Config, out_dir, ann_renames, pbar=None):
    if pbar is not None:
        pbar.set_description("Handling skeletons")
    skel_conf = config.get("neurons", default=Config())
    tag_conf = skel_conf.get("tags", default=Config())
    skel_dir = out_dir / "neurons"

    for nrn, meta in get_skeletons(
        skel_conf.get("annotated", default=[]),
        all_or_names(skel_conf),
        skel_conf.get("rename", default=dict()),
        all_or_names(tag_conf),
        tag_conf.get("rename", default=dict()),
        ann_renames,
    ):
        write_skeleton(skel_dir / str(nrn.id), nrn, meta)
    if skel_dir.exists():
        readme = join_markdown(
            skel_readme,
            skel_conf.get(README_FOOTER_KEY, default=""),
        )
        (skel_dir / "README.md").write_text(readme)
        ret = True
    else:
        ret = False

    if pbar is not None:
        pbar.update(1)

    return ret


def publish_volumes(config: Config, out_dir, ann_renames: dict[str, str], pbar=None):
    if pbar is not None:
        pbar.set_description("Fetching volumes")

    vol_conf = config.get("volumes", default=Config())
    vols, _ = get_volumes(
        vol_conf.get("annotated"),
        all_or_names(vol_conf),
        vol_conf.get("rename", default=dict()),
        ann_renames,
    )

    if vols:
        if pbar is not None:
            pbar.set_description("Writing volumes")
        write_volumes(out_dir / "volumes", vols)

        readme = join_markdown(
            vol_readme,
            vol_conf.get(README_FOOTER_KEY, default=""),
        )
        (out_dir / "volumes/README.md").write_text(readme)
        ret = True
    else:
        ret = False

    if pbar is not None:
        pbar.update(1)

    return ret


def publish_landmarks(config: Config, out_dir, pbar=None):
    if pbar is not None:
        pbar.set_description("Fetching landmarks")

    lmark_conf = config.get("landmarks", default=Config())
    grp_conf = config.get("landmarks", "groups", default=Config())
    lmarks, groups = get_landmarks(
        all_or_names(grp_conf),
        grp_conf.get("rename", default=dict()),
        all_or_names(lmark_conf),
        lmark_conf.get("rename", default=dict()),
    )

    if len(lmarks) + len(groups) > 0:
        if pbar is not None:
            pbar.set_description("Writing landmarks")
        (out_dir / "landmarks").mkdir()
        write_landmarks(out_dir / "landmarks/locations.json", lmarks, groups)

        readme = join_markdown(
            lmark_readme,
            lmark_conf.get(README_FOOTER_KEY, default=""),
        )
        (out_dir / "landmarks/README.md").write_text(readme)
        ret = True
    else:
        ret = False

    if pbar is not None:
        pbar.update(1)

    return ret


def citation_readme(config: dict):
    out = []
    cit = config.get("citation", dict())
    if doi := cit.get("doi", "").strip():
        out.append(f"The DOI of this publication is [`{doi}`](https://doi.org/{doi}).")
    if url := cit.get("url", "").strip():
        out.append(f"This publication can be accessed at {url}")
    if biblatex := cit.get("biblatex", "").strip():
        out.append(
            "This data can be cited with the below BibLaTeX snippet:\n\n"
            f"```biblatex\n{biblatex}\n```"
        )

    if out:
        out.insert(0, "")

    return "\n".join(out)


def publish_from_config(
    config_path: Path, out_dir: Path, creds_path: Optional[Path] = None
):
    timestamp = dt.datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))
    out_dir.mkdir(parents=True)
    config = Config.from_toml(config_path)
    config_hash = config.hex_digest()

    if creds_path is not None:
        creds = read_toml(creds_path)
    else:
        creds = None

    project = config.get("project", {})
    catmaid_info = {
        "server": config.get("project", "server_url"),
        "project_id": config.get("project", "project_id"),
    }

    _ = get_catmaid_instance(
        catmaid_info,
        creds,
    )

    with tqdm(total=4) as pbar:
        _, ann_renames = publish_annotations(config, out_dir, pbar)
        _ = publish_volumes(config, out_dir, ann_renames, pbar)
        _ = publish_skeletons(config, out_dir, ann_renames, pbar)
        _ = publish_landmarks(config, out_dir, pbar)

    meta = {
        "timestamp": timestamp,
        "units": project["units"],
        "config_hash": config_hash,
        "export_package": {
            "name": "catmaid_publish",
            "url": "https://github.com/clbarnes/catmaid_publish",
            "version": f"{__version__}",
        },
    }

    cit = config.get("citation", dict())
    ref = dict()

    if url := cit.get("url", "").strip():
        ref["url"] = url

    if doi := cit.get("doi", "").strip():
        ref["doi"] = f"https://doi.org/{doi}"

    if biblatex := cit.get("biblatex", "").strip():
        multiline_strings = True
        ref["biblatex"] = biblatex
    else:
        multiline_strings = False

    if ref:
        meta["reference"] = ref

    with open(out_dir / "metadata.toml", "wb") as f:
        tomli_w.dump(meta, f, multiline_strings=multiline_strings)

    with open(out_dir / "README.md", "w") as f:
        readme = join_markdown(
            README,
            project.get(README_FOOTER_KEY),
        )
        f.write(readme)


def _main(args=None):
    setup_logging(logging.INFO)
    parser = ArgumentParser("catmaid_publish", description=__doc__)
    parser.add_argument("config", type=Path, help="Path to TOML config file.")
    parser.add_argument(
        "out", type=Path, help="Path to output directory. Must not exist."
    )
    parser.add_argument(
        "credentials",
        nargs="?",
        type=Path,
        help=(
            "Path to TOML file containing CATMAID credentials "
            "(http_user, http_password, api_token as necessary). "
            "Alternatively, use environment variables "
            "with the same names upper-cased and prefixed with CATMAID_."
        ),
    )

    parsed = parser.parse_args(args)

    publish_from_config(parsed.config, parsed.out, parsed.credentials)


README = """
# README

This directory contains neuronal data exported from [CATMAID](https://catmaid.org) using the [`catmaid_publish`](https://github.com/clbarnes/catmaid_publish) python package.

See further READMEs in subdirectories for how to interpret the data.
The `catmaid_publish` package also includes a utility, `DataReader`,
to convert these files into common formats for analysis with python:

- [`navis.TreeNeuron`](https://navis.readthedocs.io/en/stable/source/generated/navis.TreeNeuron.html) for neuronal data
- [`navis.Volume`](https://navis.readthedocs.io/en/stable/source/tutorials/generated/navis.Volume.html#navis.Volume) for volumetric data
- [`networkx.DiGraph`](https://networkx.org/documentation/stable/reference/classes/digraph.html) for graph data

See also `metadata.toml` for further information about the data,
referencing, and the export itself.
""".lstrip()


if __name__ == "__main__":
    _main()
