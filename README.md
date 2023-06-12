# catmaid_publish

For the latest version, see here: <https://github.com/clbarnes/catmaid_publish> ;
for docs see here: <https://clbarnes.github.io/catmaid_publish>

Scripts for publishing data from CATMAID.
Also useful for taking a snapshot of a particular set of data for further reproducible analysis (but be careful not to mix exported data with live data from the server).

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

`catmaid_publish` fetches data from a CATMAID instance based on a configuration file.

If the instance requires authentication, credentials can be passed with environment variables or a separate TOML file.

The workflow looks like this:

```sh
# Empty config files will be created at these paths
catmaid_publish_init my_config.toml --toml-credentials my_credentials.toml

# Edit my_config.toml for your export needs
# Edit my_credentials.toml with your login details (do not share or version control this file!)

catmaid_publish my_config.toml my_export/ my_credentials.toml

# optionally, compress export into a single zip file for transfer
zip -r my_export.zip my_export
```

### `catmaid_publish_init`

Use this to initialise an empty config and optional credentials files.
If you have already set your credentials using environment variables starting with `CATMAID_`, the credentials files will be filled in.

```_catmaid_publish_init
usage: catmaid_publish_init [-h] [--toml-credentials TOML_CREDENTIALS]
                            [--env-credentials ENV_CREDENTIALS] [--ignore-env]
                            [--no-http-basic] [--no-token]
                            config

Write an empty config file and, optionally, credentials files.

positional arguments:
  config                Path to write TOML config

options:
  -h, --help            show this help message and exit
  --toml-credentials TOML_CREDENTIALS, -t TOML_CREDENTIALS
                        Path to write TOML file for credentials. Will be
                        populated by CATMAID_* environment variables if set.
  --env-credentials ENV_CREDENTIALS, -e ENV_CREDENTIALS
                        Path to write env file for credentials. Will be
                        populated by CATMAID_* environment variables if set.
  --ignore-env, -i      Ignore CATMAID_* environment variables when writing
                        credential files.
  --no-http-basic, -H   Omit HTTP basic auth from credentials file.
  --no-token, -T        Omit CATMAID API token from credentials file.
```

If you would prefer to write the config and credentials files yourself, see the [examples here](./src/catmaid_publish/).

### Configuration

Fill in the config file using [TOML formatting](https://toml.io/en/).

Citation information will be included with the export.
Project information will be used to connect to CATMAID (but sensitive credentials should be stored elsewhere).

For other data types, `all = true` means export all data of that type.
Note that this can take a very long time for common data types (e.g. neurons) in large projects.
If `all = false`, you can list the names of specific objects to be exported.
You can also rename specific objects by mapping the old name to the new one (objects to be renamed will be added to the list of objects to export).

Some objects can be annotated.
In this case, you can instead list annotations for which annotated objects will be exported.
Indirectly annotated ("sub-annotated") objects, e.g. the relationship between A and C in `annotation "A" -> annotation "B" -> neuron "C"` will also be exported.

All exported data have a pre-written `README.md` file detailing the data format and structure.
You can add additional information to the README using the `readme_footer` key.
This string will have leading and trailing whitespace stripped, and, if still non-empty, will be appended to the default README below a thematic break.

### Authentication

If your CATMAID instance requires authentication (with a CATMAID account and/or HTTP Basic authentication), fill in these details in a separate TOML file, or as environment variables (which can be loaded from a shell script file).

Passwords, API tokens etc. **MUST NOT** be tracked with git.

A credentials file simply looks like this:

```toml
# If your instance requires login to browse
api_token = "y0urc47ma1d70k3n"

# If your instance uses HTTP Basic authentication to access
http_user = "myuser"
http_password = "mypassword"
```

Or use environment variables `CATMAID_API_TOKEN`, `CATMAID_HTTP_USER`, and `CATMAID_HTTP_PASSWORD`.

### `catmaid_publish`

Once you have filled in the config file, use the `catmaid_publish` command to fetch and write the data, e.g.

```sh
# leave out the credentials path if you are using environment variables
catmaid_publish path/to/config.toml path/to/output_dir path/to/credentials.toml
```

Full usage details are here:

```_catmaid_publish
usage: catmaid_publish [-h] config out [credentials]

Export data from CATMAID in plaintext formats with simple configuration.

positional arguments:
  config       Path to TOML config file.
  out          Path to output directory. Must not exist.
  credentials  Optional path to TOML file containing CATMAID credentials
               (http_user, http_password, api_token as necessary).
               Alternatively, use environment variables with the same names
               upper-cased and prefixed with CATMAID_.

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

### Tips

In general, it's most robust to use the CATMAID UI to make an annotation specifically for your export; ideally namespaced and timestamped (e.g. `cbarnes_export_2023-02-15`).
Later exports can be a superset of this one.

#### Publication

Consider running the export once to find which objects are exported,
and determine whether any objects need renaming.
Then update your configuration with these renames.

#### Analysis snapshot

In large CATMAID projects, there are relatively few landmarks, volumes, and annotations compared to neurons.
As these are all helpful for mining data, consider exporting with `all = true` for everything except neurons.
Use the CATMAID UI (e.g. connectivity widget, graph widget, volume intersection) to annotate a superset of your neurons of interest for the export.

It is easier to bounce between local analysis and use of the CATMAID UI if you do not rename any objects in this case.

## Containerisation

This project can be containerised with [apptainer](https://apptainer.org/docs/user/main/quick_start.html) (formerly called Singularity)
(bundling it with a python environment and full OS) on linux,
so that it can be run on any system with apptainer installed.

Just run `make container` (requires sudo).

The python files are installed in the container at `/project`.

Depending on where your config and credentials files are stored, they may be [accessible to the container by default](https://apptainer.org/docs/user/main/bind_paths_and_mounts.html#system-defined-bind-paths).
Otherwise, you can manually [bind mount](https://apptainer.org/docs/user/main/bind_paths_and_mounts.html) the containing directories inside the container at runtime:

```sh
# Find the data path your environment is using, defaulting to the local ./data
DATA_PATH="$(pwd)/data"
CREDS_PATH="$(pwd)/credentials"

# Execute the command `/bin/bash` (i.e. get a terminal inside the container),
# mounting the data directory and credentials you're already using.
# Container file (.sif) must already be built
apptainer exec \
    --bind "$DATA_PATH:/data" \
    --bind "$CREDS_PATH:/credentials" \
    catmaid_publish.sif /bin/bash

# Now you're inside the container...
>>> catmaid_publish_init /data/config.toml -t /credentials/my_instance.toml
>>> catmaid_publish /data/config.toml /data/my_export /credentials/my_instance.toml
```
