from pathlib import Path

from extreqs import parse_requirement_files_dict
from setuptools import find_namespace_packages, setup

with open(Path(__file__).resolve().parent / "README.md") as f:
    readme = f.read()

req_kwargs = parse_requirement_files_dict(
    Path(__file__).resolve().parent / "requirements.txt"
)

setup(
    name="catmaid_publish",
    url="https://github.com/clbarnes/catmaid_publish",
    author="Chris L. Barnes",
    description="Scripts for publishing data from CATMAID",
    long_description=readme,
    long_description_content_type="text/markdown",
    package_dir={"": "src"},
    packages=find_namespace_packages(where="src", include=["catmaid_publish*"]),
    package_data={"catmaid_publish.package_data": ["*.toml", "*.env", "*.md"]},
    python_requires=">=3.9, <4.0",
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    entry_points={
        "console_scripts": [
            "catmaid_publish=catmaid_publish.main:_main",
            "catmaid_publish_init=catmaid_publish.initialise:_main",
        ]
    },
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    **req_kwargs,
)
