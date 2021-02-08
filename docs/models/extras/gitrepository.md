# Git Repositories

Some text-based content is more conveniently stored in a separate Git repository rather than internally in the NetBox database. Such a repository may currently include any or all of the following for NetBox to consume:

* Job source files and associated data files,
* Configuration context data
* Export templates
* Additional data types as registered by any installed plugins

## Repository Configuration

When defining a Git repository for NetBox to consume, the `name`, `remote URL`, and `branch` parameters are mandatory - the name acts as a unique identifier, and the remote URL and branch are needed for NetBox to be able to locate and access the specified repository. Additionally, if the repository is private on GitHub, you may specify a [`token`](https://docs.github.com/en/free-pro-team@latest/github/authenticating-to-github/creating-a-personal-access-token) that can be used to grant access to the repository.

Whenever a Git repository record is created, updated, or deleted, NetBox automatically enqueues a background task that will asynchronously execute to clone, fetch, or delete a local copy of the Git repository on the filesystem (located under `GIT_ROOT`) and then create, update, and/or delete any database records managed by this repository. The progress and eventual outcome of this background task are recorded as a `JobResult` record that may be viewed from the Git repository user interface.

## Repository Structure

### Jobs

Jobs defined in Python files located in a `/jobs/` directory at the root of a Git repository will automatically be discovered by NetBox and made available to be run as a job, just as they would be if manually installed to the `$JOBS_ROOT` directory. Note that there **must** be an `__init__.py` file in the `/jobs/` directory.

### Configuration Contexts

Config contexts may be provided as JSON or YAML files located in `/config_contexts/`.

Files in the root of the `/config_contexts/` directory will be imported as described below, with no special meaning attributed to their filenames (the name of the constructed config context will be taken from the `_metadata` within the file, not the filename).

Alternatively, files can be placed in `/config_contexts/<filter>/<slug>.[json|yaml]`, in which case their path and filename will be taken as an implied grouping for the scope of the context. For example:

```shell
config_contexts/
  context_1.json   # JSON data will be imported as-is
  context_2.yaml   # YAML data will be imported as-is
  regions/
    nyc.yaml       # YAML data, with implied scoping to the Region with slug "nyc"
  sites/
    nyc-01.json    # JSON data, with implied scoping to the Site with slug "nyc-01"
```

After loading and potentially extending the JSON or YAML data, the key `_metadata` will be extracted from the loaded data and used to define the config context's metadata; all remaining data will form the config context data dictionary. For example, the below JSON file defines a config context with two keys `ntp-servers` and `syslog-servers` in its data:

```json
{
    "_metadata": {
        "name": "Region NYC servers",
        "weight": 1000,
        "description": "NTP and Syslog servers for region NYC",
        "is_active": true,
        "regions": [{"slug": "nyc"}]
    },
    "ntp-servers": [
        "172.16.10.22",
        "172.16.10.33"
    ],
    "syslog-servers": [
        "172.16.9.100",
        "172.16.9.101"
    ]
}
```

Within the `_metadata`, the `name` key is always required; all other metadata keys are optional and will take on default values if omitted.

For files in the root of the `/config_contexts/` directory, a single file may define a single config context, or it may contain a list of config context data definitions, as in the following example:

```yaml
---
- _metadata:
    name: "Router hostname pattern"
    roles:
      - slug: "router"
  hostname_pattern_string: "rtr-.+"
- _metadata:
    name: "Console Server hostname pattern"
    roles:
      - slug: "console-server"
  hostname_pattern_string: "cs-.+"
- _metadata:
    name: "Switches hostname pattern"
    roles:
      - slug: "aggr-switch"
      - slug: "services-switch"
  hostname_pattern_string: "switch-.+"
- _metadata:
    name: "Appliance hostname pattern"
    roles:
      - slug: "security-appliance"
  hostname_pattern_string: "fw-.+"
...
```

!!! note
    Git repositories cannot currently be used to define per-device or per-virtual-machine "local" configuration context data.

### Export Templates

Export templates may be provided as files located in `/export_templates/<grouping>/<model>/<template_file>`; for example, a JSON export template for Device records might be `/export_templates/dcim/device/mytemplate.json`.

* The name of a discovered export template will be presented in NetBox as `<repository name>: <filename>`.
* The MIME type of a file rendered from a discovered export template will always be the default `text/plain`.
* The file extension of a file rendered from a discovered export template will match that of the template itself (so, in the above example, the extension would be `.json`)
