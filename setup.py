from pathlib import Path

from setuptools import find_packages, setup
from extreqs import parse_requirement_files

with open(Path(__file__).resolve().parent / "README.md") as f:
    readme = f.read()

install_requires, extras_require = parse_requirement_files(
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
    packages=find_packages(where="src", include=["catmaid_publish*"]),
    install_requires=install_requires,
    extras_require=extras_require,
    python_requires=">=3.9, <4.0",
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    entry_points={"console_scripts": ["catmaid_publish=catmaid_publish.main:_main"]},
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
)
