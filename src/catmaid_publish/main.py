from argparse import ArgumentParser
from pathlib import Path
import json
from typing import Optional, Any
import datetime as dt
import logging

from tqdm import tqdm

from . import __version__
from .utils import setup_logging
from .io_helpers import hash_toml, read_toml, get_catmaid_instance
from .annotations import get_annotations, write_annotation_graph, README as ann_readme
from .landmarks import get_landmarks, write_landmarks, README as lmark_readme
from .skeletons import get_skeletons, write_skeleton, README as skel_readme
from .volumes import get_volumes, write_volumes, README as vol_readme


def publish_annotations(config: dict[str, Any], out_dir: Path, pbar=None):
    if pbar is not None:
        pbar.set_description("Fetching annotations")

    ann_conf = config.get("annotations", dict())
    ann_children, ann_renames = get_annotations(
        ann_conf.get("annotated", []),
        ann_conf.get("names", []),
        ann_conf.get("rename", dict()),
    )
    if ann_children:
        if pbar is not None:
            pbar.set_description("Writing annotations")
        (out_dir / "annotations").mkdir()
        (out_dir / "annotations/README.md").write_text(ann_readme)
        write_annotation_graph(
            out_dir / "annotations/annotation_graph.json", ann_children
        )
        ret = True
    else:
        ret = False

    if pbar is not None:
        pbar.update(1)

    return ret, ann_renames


def publish_skeletons(config, out_dir, ann_renames, pbar=None):
    if pbar is not None:
        pbar.set_description("Handling skeletons")
    skel_conf = config.get("skeletons", dict())
    tag_conf = skel_conf.get("tags", dict())
    skel_dir = out_dir / "neurons"

    for nrn, meta in get_skeletons(
        skel_conf.get("annotated", []),
        skel_conf.get("names", []),
        skel_conf.get("rename", dict()),
        tag_conf.get("names", []),
        tag_conf.get("rename", dict()),
        ann_renames,
    ):
        write_skeleton(skel_dir / str(nrn.id), nrn, meta)
    if skel_dir.exists():
        (skel_dir / "README.md").write_text(skel_readme)
        ret = True
    else:
        ret = False

    if pbar is not None:
        pbar.update(1)

    return ret


def publish_volumes(config, out_dir, pbar=None):
    if pbar is not None:
        pbar.set_description("Fetching volumes")

    vol_conf = config.get("volumes", dict())
    vols, _ = get_volumes(
        vol_conf.get("names", []),
        vol_conf.get("rename", dict()),
    )

    if vols:
        if pbar is not None:
            pbar.set_description("Writing volumes")
        write_volumes(out_dir / "volumes", vols)
        (out_dir / "volumes/README.md").write_text(vol_readme)
        ret = True
    else:
        ret = False

    if pbar is not None:
        pbar.update(1)

    return ret


def publish_landmarks(config, out_dir, pbar=None):
    if pbar is not None:
        pbar.set_description("Fetching landmarks")

    lmark_conf = config.get("landmarks", dict())
    lmarks, groups = get_landmarks(
        lmark_conf.get("groups", []),
        lmark_conf.get("group_rename", dict()),
        lmark_conf.get("names", []),
        lmark_conf.get("rename", dict()),
    )

    if len(lmarks) + len(groups) > 0:
        if pbar is not None:
            pbar.set_description("Writing landmarks")
        (out_dir / "landmarks").mkdir()
        write_landmarks(out_dir / "landmarks/locations.json", lmarks, groups)
        (out_dir / "landmarks/README.md").write_text(lmark_readme)
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
            f"This data can be cited with the below BibLaTeX snippet:\n\n```biblatex\n{biblatex}\n```"
        )

    if out:
        out.insert(0, "")

    return "\n".join(out)


def publish_from_config(
    config_path: Path, out_dir: Path, creds_json: Optional[Path] = None
):
    timestamp = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%MZ")
    out_dir.mkdir(parents=True)
    config = read_toml(config_path)
    config_hash = hash_toml(config_path)
    if creds_json is not None:
        creds = json.loads(creds_json.read_text())
    else:
        creds = None

    project = config.get("project", {})
    catmaid_info = {
        "server": project["server_url"],
        "project_id": project["project_id"],
    }

    cm = get_catmaid_instance(
        catmaid_info,
        creds,
    )

    with tqdm(total=4) as pbar:
        has_landmarks = publish_landmarks(config, out_dir, pbar)
        has_volumes = publish_volumes(config, out_dir, pbar)
        has_anns, ann_renames = publish_annotations(config, out_dir, pbar)
        has_skels = publish_skeletons(config, out_dir, ann_renames, pbar)

    readme_lines = [
        "# README",
        "",
        f"This dataset was generated using `catmaid_publish v{__version__}`at `{timestamp}` from a config file with hash `{config_hash}`.",
        citation_readme(config),
        "",
        "Data and additional information can be found in the following directories:",
    ]

    if has_landmarks:
        readme_lines.append("- `landmarks`")
    if has_volumes:
        readme_lines.append("- `volumes`")
    if has_anns:
        readme_lines.append("- `annotations`")
    if has_skels:
        readme_lines.append("- `neurons`")

    readme_lines.append("")
    readme_lines.append(f"Spatial data are in `{project['units']}`.\n")
    readme = "\n".join(readme_lines)
    (out_dir / "README.md").write_text(readme)


def _main(args=None):
    setup_logging(logging.INFO)
    parser = ArgumentParser("catmaid_publish")
    parser.add_argument("config", type=Path, help="Path to TOML config file.")
    parser.add_argument("out", type=Path, help="Path to output directory. Must not exist.")
    parser.add_argument("credentials", nargs="?", type=Path, help="Path to JSON file containing CATMAID credentials. Alternatively, use environment variables.")

    parsed = parser.parse_args(args)

    publish_from_config(parsed.config, parsed.out, parsed.credentials)


if __name__ == "__main__":
    _main()
