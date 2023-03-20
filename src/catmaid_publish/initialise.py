#!/usr/bin/env python3
"""
Write an empty config file and, optionally, credentials files.
"""
import logging
import os
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any, Optional

if sys.version_info >= (3, 10):
    from importlib.resources import files
else:
    from importlib_resources import files

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from .utils import setup_logging

logger = logging.getLogger(__name__)

PREFIX = "CATMAID_"
package_data = files("catmaid_publish.package_data")


def get_creds_placeholders():
    return tomllib.loads(example_creds_toml())


def example_config():
    return package_data.joinpath("config.toml").read_text()


def example_creds_env():
    return package_data.joinpath("creds.env").read_text()


def example_creds_toml():
    return package_data.joinpath("creds.toml").read_text()


def from_env_name(s):
    return s[len(PREFIX) :].lower()


def to_env_name(s):
    return f"{PREFIX}{s.upper()}"


def read_env_vars() -> dict[str, Any]:
    out = dict()
    for k, v in os.environ.items():
        if not k.startswith(PREFIX):
            continue
        out[from_env_name(k)] = v
    return out


def make_creds_env_content(
    envvars: dict[str, Any],
    placeholders: dict[str, str],
    include_http_basic: bool,
    include_api_token: bool,
):
    content = example_creds_env()
    if include_http_basic:
        content = content.replace(
            placeholders["http_user"], envvars.get("http_user", "")
        )
        content = content.replace(
            placeholders["http_password"], envvars.get("http_password", "")
        )
    else:
        content.replace("CATMAID_HTTP", "# CATMAID_HTTP")

    if include_api_token:
        content = content.replace(
            placeholders["api_token"], envvars.get("api_token", "")
        )
    else:
        content.replace("CATMAID_API_TOKEN", "# CATMAID_API_TOKEN")

    return content


def make_creds_toml_content(
    envvars: dict[str, Any],
    placeholders: dict[str, str],
    include_http_basic: bool,
    include_api_token: bool,
):
    content = example_creds_toml()

    if include_http_basic:
        content = content.replace(
            placeholders["http_user"], envvars.get("http_user", "")
        )
        content = content.replace(
            placeholders["http_password"], envvars.get("http_password", "")
        )
    else:
        content.replace("http_", "# http_")

    if include_api_token:
        content = content.replace(
            placeholders["api_token"], envvars.get("api_token", "")
        )
    else:
        content.replace("api_token", "# api_token")

    return content


def make_config_content(envvars: dict[str, Any]):
    content = example_config()

    if "project_id" in envvars:
        content = content.replace(
            "project_id = 1", f"project_id = {envvars['project_id']}"
        )

    if "server_url" in envvars:
        content = content.replace(
            '"https://url.to/my_instance"',
            f'"{envvars["server_url"]}"',
        )

    return content


def main(
    config: Path,
    env_credentials: Optional[Path] = None,
    toml_credentials: Optional[Path] = None,
    ignore_env: bool = False,
    include_http_basic: bool = True,
    include_api_token: bool = True,
):
    if config.suffix != ".toml" or (
        toml_credentials and toml_credentials.suffix != ".toml"
    ):
        raise ValueError("TOML file should use the suffix '.toml'")

    if env_credentials is not None and toml_credentials is not None:
        logger.warning("Writing both .env and .toml credentials; do you need both?")

    if ignore_env:
        envvars = dict()
    else:
        envvars = read_env_vars()

    placeholders = get_creds_placeholders()

    config.write_text(make_config_content(envvars))

    if env_credentials:
        s = make_creds_env_content(
            envvars, placeholders, include_http_basic, include_api_token
        )
        Path(env_credentials).write_text(s)

    if toml_credentials:
        s = make_creds_toml_content(
            envvars, placeholders, include_http_basic, include_api_token
        )
        Path(toml_credentials).write_text(s)


def _main(args=None):
    setup_logging(logging.INFO)
    parser = ArgumentParser("catmaid_publish_init", description=__doc__)
    parser.add_argument("config", type=Path, help="Path to write TOML config")
    parser.add_argument(
        "--toml-credentials",
        "-t",
        type=Path,
        help=(
            "Path to write TOML file for credentials. "
            "Will be populated by CATMAID_* environment variables if set."
        ),
    )
    parser.add_argument(
        "--env-credentials",
        "-e",
        type=Path,
        help=(
            "Path to write env file for credentials. "
            "Will be populated by CATMAID_* environment variables if set."
        ),
    )
    parser.add_argument(
        "--ignore-env",
        "-i",
        action="store_true",
        help=("Ignore CATMAID_* environment variables when writing credential files."),
    )
    parser.add_argument(
        "--no-http-basic",
        "-H",
        action="store_true",
        help="Omit HTTP basic auth from credentials file.",
    )
    parser.add_argument(
        "--no-token",
        "-T",
        action="store_true",
        help="Omit CATMAID API token from credentials file.",
    )

    parsed = parser.parse_args(args)

    main(
        parsed.config,
        parsed.env_credentials,
        parsed.toml_credentials,
        parsed.ignore_env,
        not parsed.no_http_basic,
        not parsed.no_token,
    )
