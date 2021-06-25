# Git Repositories

Some text-based content is more conveniently stored in a separate Git repository rather than internally in the Nautobot database. Such a repository may currently include any or all of the following for Nautobot to consume:

* Job source files and associated data files,
* Configuration context data
* Export templates
* Additional data types as registered by any installed plugins

!!! important
    Nautobot's Git integration depends on the availability of the `git` program. If `git` is not installed, Nautobot will be unable to pull data from Git repositories.

## Repository Configuration

When defining a Git repository for Nautobot to consume, the `name`, `remote URL`, and `branch` parameters are mandatory - the name acts as a unique identifier, and the remote URL and branch are needed for Nautobot to be able to locate and access the specified repository. Additionally, if the repository is private you may specify a `token` and the token `username` that can be used to grant access to the repository.

The token implementation can vary from Git provider to Git provider, the following providers have been confirmed to work. In theory, additional providers using the same pattern will work, but there is currently no specific support for all providers.

* GitHub's [`token`](https://docs.github.com/en/free-pro-team@latest/github/authenticating-to-github/creating-a-personal-access-token) does not require a `username`.
* GitLab's [`token`](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html) requires a `username`, conventions are to use the username "oauth2". In addition, GitLab's [deploy tokens](https://docs.gitlab.com/ee/user/project/deploy_tokens/) are also supported.
* For Bitbucket, there are two options: [personal access tokens](https://confluence.atlassian.com/bitbucketserver/personal-access-tokens-939515499.html) or [OAuth2](https://developer.atlassian.com/cloud/bitbucket/oauth-2/) depending on the product.

Whenever a Git repository record is created, updated, or deleted, Nautobot automatically enqueues a background task that will asynchronously execute to clone, fetch, or delete a local copy of the Git repository on the filesystem (located under [`GIT_ROOT`](../../../configuration/optional-settings/#git_root)) and then create, update, and/or delete any database records managed by this repository. The progress and eventual outcome of this background task are recorded as a `JobResult` record that may be viewed from the Git repository user interface.

## Repository Structure

### Jobs

Jobs defined in Python files located in a `/jobs/` directory at the root of a Git repository will automatically be discovered by Nautobot and made available to be run as a job, just as they would be if manually installed to the [`JOBS_ROOT`](../../../configuration/optional-settings/#jobs_root) directory.

!!! note
    There **must** be an `__init__.py` file in the `/jobs/` directory.

### Configuration Contexts

Config contexts may be provided as JSON or YAML files located in `/config_contexts/`.

Files in the root of the `/config_contexts/` directory will be imported as described below, with no special meaning attributed to their filenames (the name of the constructed config context will be taken from the `_metadata` within the file, not the filename).

Additionally or as an alternative, files can be placed in `/config_contexts/<filter>/<slug>.[json|yaml]`, in which case their path and filename will be taken as an implied scope for the context. For example:

```shell
config_contexts/
  context_1.json   # JSON data will be imported as-is, with scoping derived from its contents
  context_2.yaml   # YAML data will be imported as-is, with scoping derived from its contents
  devices/
    rtr-01.yaml    # YAML data, local to the Device named "rtr-01"
  regions/
    nyc.yaml       # YAML data, with implied scoping to the Region with slug "nyc"
  sites/
    nyc-01.json    # JSON data, with implied scoping to the Site with slug "nyc-01"
  virtual_machines/
    vm001.json     # JSON data, local to the VirtualMachine named "vm001"
```

#### Grouped/Scoped Configuration Contexts

After loading and potentially extending the JSON or YAML data with any implied scoping, the key `_metadata` will be extracted from the loaded data and used to define the config context's metadata; all remaining data will form the config context data dictionary. For example, the below JSON file defines a config context with weight 1000, scoped to the region with slug `nyc`, with two keys `ntp-servers` and `syslog-servers` in its config context data:

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

For files in the root of the `/config_contexts/` directory, a single file may define a single config context as above, or alternatively it may contain a list of config context data definitions, as in the following example:

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

#### Local Configuration Contexts

Files in a `config_contexts/devices/` and/or `config_contexts/virtual_machines/` directory will be used to populate "local" config context data for individual devices or virtual machines. For these files, the device/VM name will always be taken from the filename, and the data in the file will be used precisely as-is (there is no need, or support, for a `_metadata` key in these files).

!!! note
    While virtual machines are always uniquely identified by their name, it is possible for devices associated with different sites and/or tenants to share an identical name. Currently, Nautobot is unable to automatically apply local config context via Git to devices that have a non-globally-unique name (or no name at all).

### Configuration Context Schemas

Config contexts may be provided as JSON or YAML files located in `/config_context_schemas/`.

Files in the root of the `/config_context_schemas/` directory will be imported as described below, with no special meaning attributed to their filenames (the name of the constructed config context schema will be taken from the `_metadata` within the file, not the filename).

```shell
config_context_schema/
  context_schema_1.json   # JSON data will be imported as-is, with scoping derived from its contents
  context_schema_2.yaml   # YAML data will be imported as-is, with scoping derived from its contents
```

When loading the schema, the key `_metadata` will be extracted from the loaded data and used to define the config context schemer's metadata; all remaining data will form the config context data schema.

Inside of the metadata there is a list called `config_contexts`, this holds all of the config contexts the schema applies too. The config contexts are defined through dictionaries with attributes which can identify the context. Below shows that the schema applies to a config context with a name of `"Config Context 1"`.

JSON example:

``` json
{
  "_metadata": {
    "name": "Config Context Schema 1",
    "description": "Schema for defining first names, last names and ages.",
    "config_contexts": [
      {"name": "Config Context 1"},
    ],
  },
  "data_schema": {
    "title": "Person",
    "type": "object",
    "properties": {
      "firstName": {
        "type": "string",
        "description": "The person's first name.",
      },
      "lastName": {
        "type": "string",
        "description": "The person's last name.",
      },
      "age": {
        "description": "Age in years which must be equal to or greater than zero.",
        "type": "integer",
        "minimum": 0,
      },
    },
  },
}
```

YAML example:

``` yaml
---
- _metadata:
    name: "Config Context Schema 1"
    description: "Schema for config contexts"
    config_contexts:
    - name: "Config Context 1"
  data_schema:
    $id: "https://example.com/person.schema.json"
    $schema: "https://json-schema.org/draft/2020-12/schema"
    title: "Person"
    type: "object"
    properties:
      firstName:
        type: "string"
        description: "The person's first name"
      lastName:
        type: "string"
        description: "The person's last name."
      age:
        type: "integer"
        description: "Age in years which must be equal to or greater than zero"
        minimum: 0
```

### Export Templates

Export templates may be provided as files located in `/export_templates/<grouping>/<model>/<template_file>`; for example, a JSON export template for Device records might be `/export_templates/dcim/device/mytemplate.json`.

* The name of a discovered export template will be presented in Nautobot as `<repository name>: <filename>`.
* The MIME type of a file rendered from a discovered export template will always be the default `text/plain`.
* The file extension of a file rendered from a discovered export template will match that of the template itself (so, in the above example, the extension would be `.json`)
