# catmaid_publish

For the latest version, see here: https://github.com/clbarnes/catmaid_publish ;
for docs see here: https://clbarnes.github.io/catmaid_publish

Scripts for publishing data from CATMAID

Originally created using
[cookiecutter](https://github.com/cookiecutter/cookiecutter) and
[clbarnes/python-template-sci](https://github.com/clbarnes/python-template-sci).

## Installation

First, ensure you're working in a virtual environment:

```sh
# create a virtual environment if you don't have one
python -m venv --prompt catmaid_publish venv

# activate it
source venv/bin/activate
```

Then install the package, using one of:

```sh
# from github
pip install git+https://github.com/clbarnes/catmaid_publish.git

# a local copy of the repo, from within the parent directory
pip install -e .
```

## Usage

### Configuration

Copy `data/example_config.toml` and fill in the fields describing which data you want to export.

Citation information will be included with the export.
Project information will be used to connect to CATMAID (but sensitive credentials should be stored elsewhere).

For other data types, `all = true` means export all data of that type.
Note that this can take a very long time for common data types (e.g. skeletons) in large projects.
If `all = false`, you can list the names of specific objects to be exported.
You can also rename specific objects by mapping the old name to the new one (objects to be renamed will be added to the list of objects to export).

Some objects can be annotated.
In this case, you can instead list annotations for which directly annotated objects will be exported.
Indirectly annotated ("sub-annotated") objects, e.g. the relationship between A and C in `annotation "A" -> annotation "B" -> skeleton "C"` will not be exported.

### Authentication

If your CATMAID instance requires authentication (with a CATMAID account and/or HTTP Basic authentication), fill in these details in a separate TOML file, or as environment variables.
Examples are in the `credentials/` directory: copy these files before filling in your own details.

Passwords, API tokens etc. **MUST NOT** be tracked with git.
Files in the `credentials/` directory are ignored by git (except the example files), so this is a good place to keep them.

### `catmaid_publish`

Once this config file is written, use the `catmaid_publish` command to fetch and write the data, e.g.

```sh
catmaid_publish path/to/config.toml path/to/output_dir path/to/credentials.toml
```

Full usage details are here:

```_catmaid_publish
usage: catmaid_publish [-h] config out [credentials]

Export data from CATMAID in plaintext formats with simple configuration.

positional arguments:
  config       Path to TOML config file.
  out          Path to output directory. Must not exist.
  credentials  Path to TOML file containing CATMAID credentials (http_user,
               http_password, api_token as necessary). Alternatively, use
               environment variables with the same names upper-cased and
               prefixed with CATMAID_.

options:
  -h, --help   show this help message and exit
```

### Output

README files in the output directory hierarchy describe the formats of the included data.
All data are sorted deterministically and in plain text, and are highly compressible.

#### Reading

As detailed in the top-level README of the exported data, this package contains a utility for reading an export into common python data structures for neuronal analysis.

For example:

```python
from catmaid_publish import DataReader, ReadSpec, Location
import networkx as nx
import navis

reader = DataReader("path/to/exported/data")

annotation_graph: nx.DiGraph = reader.annotations.get_graph()
neuron: navis.TreeNeuron = reader.neurons.get_by_name(
    "my neuron",
    ReadSpec(nodes=True, connectors=False, tags=True),
)
landmark_locations: list[Location] = list(reader.landmarks.get_all())
volume: navis.Volume = reader.volumes.get_by_name("my volume")
```

## Containerisation

This project can be containerised with [apptainer](https://apptainer.org/docs/user/main/quick_start.html) (formerly called Singularity)
(bundling it with a python environment and full OS) on linux,
so that it can be run on any system with apptainer installed.

Just run `make container` (requires sudo).

The python files are installed in the container at `/project`.
To improve container size and flexibility, the `./data/` directory is not included.
To improve flexibility and security, the `./credentials/` directory is not included.

You can [bind mount](https://apptainer.org/docs/user/main/bind_paths_and_mounts.html) these directories inside the container at runtime:

```sh
# Find the data path your environment is using, defaulting to the local ./data
DATA_PATH="${CATMAID_PUBLISH_DATA:-$(pwd)/data}"
CREDS_PATH="$(pwd)/credentials"

# Execute the command `/bin/bash` (i.e. get a terminal inside the container),
# mounting the data directory and credentials you're already using.
# Container file (.sif) must already be built
apptainer exec \
    --bind "$DATA_PATH:/project/data" \
    --bind "$CREDS_PATH:/project/credentials" \
    catmaid_publish.sif /bin/bash
```
