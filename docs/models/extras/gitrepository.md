# Git Repositories

Some text-based content is more conveniently stored in a separate Git repository rather than internally in the NetBox database. Such a repository may currently include any or all of the following for NetBox to consume:

* [Custom job](../../additional-features/custom-jobs.md) source files and associated data files,
* [Configuration context](configcontext.md) data
* [Export templates](../../additional-features/export-templates.md)
* Additional data as [registered](../../plugins/development.md#loading-data-from-a-git-repository) by any installed plugins

## Repository Configuration

When defining a Git repository for NetBox to consume, the `name`, `URL`, and `branch` parameters are mandatory - the name acts as a unique identifier, and the remote URL and branch are needed for NetBox to be able to locate and access the specified repository. Additionally, if the repository is private on GitHub, you may specify a [`token`](https://docs.github.com/en/free-pro-team@latest/github/authenticating-to-github/creating-a-personal-access-token) that can be used to grant access to the repository.

## Repository Structure

### Custom Jobs

Custom jobs defined in Python files located in a `/custom_jobs/` directory at the root of a Git repository will automatically be discovered by NetBox and made available to be run as a custom job, just as they would be if manually installed to the `$CUSTOM_JOBS_ROOT` directory. Note that there **must** be an `__init__.py` file in the `/custom_jobs/` directory.

### Configuration Contexts

Config contexts may be provided as JSON or YAML files located in `/config_contexts/`. The expected format of these files is similar to that of the `/api/extras/config-contexts/` REST API POST endpoint, with the exception that the grouping(s) (regions, sites, roles, tags, etc.) associated with a given config context can be identified by any appropriate combination of unique parameters, not just by their database primary key(s). Most commonly you will identify groupings by their `name` or `slug` values, for example:

```json
{
    "name": "Region NYC servers",
    "weight": 1000,
    "description": "NTP and Syslog servers for region NYC",
    "is_active": true,
    "regions": [{"slug": "nyc"}],
    "data": {
        "ntp-servers": [
            "172.16.10.22",
            "172.16.10.33"
        ],
        "syslog-servers": [
            "172.16.9.100",
            "172.16.9.101"
        ]
    }
}
```

A single file may define a single config context, or it may contain a list of config context data definitions, as in the following example:

```yaml
---
- "name": "Router hostname pattern"
  "weight": 1000
  "description": "Hostname pattern for device role Router"
  "is_active": true
  "roles":
    - "slug": "router"
  "data":
    "hostname_pattern": "rtr-.+"
- "name": "Console Server hostname pattern"
  "weight": 1000
  "description": "Hostname pattern for device role Console Server"
  "is_active": true
  "roles":
    - "slug": "console-server"
  "data":
    "hostname_pattern": "cs-.+"
- "name": "Switches hostname pattern"
  "weight": 1000
  "description": "Hostname pattern for device roles Aggregation Switch and Services Switch"
  "is_active": true
  "roles":
    - "slug": "aggr-switch"
    - "slug": "services-switch"
  "data":
    "hostname_pattern": "switch-.+"
- "name": "Appliance hostname pattern"
  "weight": 1000
  "description": "Hostname pattern for device role Security Appliance"
  "is_active": true
  "roles":
    - "slug": "security-appliance"
  "data":
    "hostname_pattern": "fw-.+"
...
```

!!! note
    As each config context's name is specified in the `name` field of the JSON or YAML data, the filename of the file providing this data is not currently used in any way by NetBox. As a best practice, you should nonetheless generally use a filename that is at least similar to the data's `name` field.

### Export Templates

Export templates may be provided as files located in `/export_templates/<grouping>/<model>/<template_file>`; for example, a JSON export template for Device records might be `/export_templates/dcim/device/mytemplate.json`.

* The name of a discovered export template will be presented in NetBox as `<repository name>: <filename>`.
* The MIME type of a file rendered from a discovered export template will always be the default `text/plain`.
* The file extension of a file rendered from a discovered export template will match that of the template itself (so, in the above example, the extension would be `.json`)
