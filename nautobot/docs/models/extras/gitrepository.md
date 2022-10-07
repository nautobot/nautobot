# Git Repositories

Some text-based content is more conveniently stored in a separate Git repository rather than internally in the Nautobot database. Such a repository may currently include any or all of the following for Nautobot to consume:

* Job source files and associated data files,
* Configuration context data
* Export templates
* Additional data types as registered by any installed plugins

!!! important
    Nautobot's Git integration depends on the availability of the `git` program. If `git` is not installed, Nautobot will be unable to pull data from Git repositories.

## Repository Configuration

When defining a Git repository for Nautobot to consume, the `name`, `remote URL`, and `branch` parameters are mandatory - the name acts as a unique identifier, and the remote URL and branch are needed for Nautobot to be able to locate and access the specified repository. Additionally, if the repository is private you may specify a `token` and any associated `username` that can be used to grant access to the repository.

!!! warning
    Beginning in Nautobot 1.2, there are two ways to define a `token` and/or `username` for a Git repository -- either by directly configuring them into the repository definition, or by associating the repository with a [secrets group](./secretsgroup.md) record (this latter approach is new in Nautobot 1.2). The direct-configuration approach should be considered as deprecated, as it is less secure and poses a number of maintainability issues. If at all possible, you should use a secrets group instead. The direct-configuration approach may be removed altogether as an option in a future release of Nautobot.

The token implementation can vary from Git provider to Git provider, the following providers have been confirmed to work. In theory, additional providers using the same pattern will work, but there is currently no specific support for all providers.

* GitHub's [`token`](https://docs.github.com/en/free-pro-team@latest/github/authenticating-to-github/creating-a-personal-access-token) does not require a `username`.
* GitLab's [`token`](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html) requires a `username`, conventions are to use the username "oauth2". In addition, GitLab's [deploy tokens](https://docs.gitlab.com/ee/user/project/deploy_tokens/) are also supported.
* For Bitbucket, there are two options: [personal access tokens](https://confluence.atlassian.com/bitbucketserver/personal-access-tokens-939515499.html) or [OAuth2](https://developer.atlassian.com/cloud/bitbucket/oauth-2/) depending on the product.

!!! note
    When defining a [secrets group](./secretsgroup.md) for a Git repository, the group must contain assigned secret(s) with an *access type* of `HTTP(S)` and *secret type(s)* of `Token` (and `Username`, if required by the provider).

Whenever a Git repository record is created, updated, or deleted, Nautobot automatically enqueues a background task that will asynchronously execute to clone, fetch, or delete a local copy of the Git repository on the filesystem (located under [`GIT_ROOT`](../../configuration/optional-settings.md#git_root)) and then create, update, and/or delete any database records managed by this repository. The progress and eventual outcome of this background task are recorded as a `JobResult` record that may be viewed from the Git repository user interface.

!!! important
    The repository branch must exist and have a commit against it. At this time, Nautobot will not initialize an empty repository.

!!! note
    If you are using a self-signed Git repository, you will need to set the environment variable `GIT_SSL_NO_VERIFY="1"`
    in order for the repository to sync.

## Repository Structure

### Jobs

Jobs defined in Python files located in a `/jobs/` directory at the root of a Git repository will automatically be discovered by Nautobot and made available to be run as a job, just as they would be if manually installed to the [`JOBS_ROOT`](../../configuration/optional-settings.md#jobs_root) directory.

!!! note
    There **must** be an `__init__.py` file in the `/jobs/` directory.

!!! note
    Just as with jobs manually installed in `JOBS_ROOT`, jobs provided by a Git repository do not support inter-module relative Python imports (i.e., you cannot package Python "libraries" into a Git repository and then import them from Jobs in that repository). If you need to import libraries from Jobs, the libraries either must be installed as a standard Python packaging dependency or as a Nautobot plugin.

When syncing or re-syncing a Git repository, the Nautobot database records corresponding to any provided jobs will automatically be refreshed. If a job is removed as a result of the sync, the corresponding database record will *not* be automatically deleted, but will be marked as `installed = False` and will no longer be runnable. A user with appropriate access permissions can delete leftover `Job` database records if desired, but note that this will result in any existing `JobResult` records no longer having a direct reference back to the `Job` that they originated from.

### Configuration Contexts

Config contexts may be provided as JSON or YAML files located in `/config_contexts/`. There are three different types of config context scopes; **explicit**, **implicit**, and **local**.

* **Explicit**: Defined as JSON or YAML files at the root of the `/config_contexts/` folder. Multiple config contexts can be specified within the each file. The metadata regarding the naming and scoping of the config context is determined by the `_metadata` key for each list element.
* **Implicit**: They're defined using a specific folder and file structure to apply the config context to a specific scope.
* **Local**: Defined at the device/virtual machine level and only being applied to the specific device/virtual machine.

#### Metadata

The metadata used to create the config context has the following options and is specified by the `_metadata` key.

| Key         | Required | Default | Description                                                                       |
| ----------- | -------- | ------- | --------------------------------------------------------------------------------- |
| name        | True     | N/A     | The name that will be assigned to the Config Context                              |
| weight      | False    | 1000    | The weight that will be assigned to the Config Context that determines precedence |
| description | False    | N/A     | The description applied to the Config Context                                     |
| is_active   | False    | True    | Whether or not the Config Context is active                                       |
| schema      | False    | N/A     | Config Context Schema that it should be validated against                         |

There are several other keys that can be defined that match the scope of what the Config Context will be assigned to.

Here is an example `_metadata` key defined:

```json
{
    "_metadata": {
        "name": "Region NYC servers",
        "weight": 1000,
        "description": "NTP and Syslog servers for region NYC",
        "is_active": true,
        "regions": [{"slug": "nyc"}],
        "schema": "Config Context Schema 1"
    },
    "acl": {
        "definitions": {
            "named ": {
                "PERMIT_ROUTES": [
                  "10 permit ip any any"
                ]
            }
        }
    },
    "route-maps": {
        "PERMIT_CONN_ROUTES": {
            "seq": 10,
            "statements": [
                "match ip address PERMIT_ROUTES"
            ],
            "type": "permit"
        }
    }
}
```

!!! important
    The only config context scope that does not require any metadata defined is the local configuration context

#### Explicit Config Contexts

As stated above, these **explicit** files live at the root of `/config_contexts`. These files will be imported as described below, with no special meaning attributed to their filenames (the name of the constructed config context will be taken from the `_metadata` key within the file, not the filename). To provide a visual, the `context_1.json` and `context_2.yml` are **explicit** config context scopes.

```shell
config_contexts/
  context_1.json   # JSON data will be imported as-is, with scoping explicit from its contents
  context_2.yaml   # YAML data will be imported as-is, with scoping explicit from its contents
```

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

The `_metadata` key will map to the attributes required when creating a config context via the UI or API such as name and the scope of the config context. If we take a look at the first element, the name assigned to the config context will be `"Router hostname pattern"` and be scoped to `roles` with a slug of `router`.

Any key/value pair defined at the same level as `_metadata` will be converted to the config context data. Keeping with the first element, it will have a key set as `hostname_pattern_string` with a value of `rtr-.+`.

#### Implicit Config Contexts

Implicit config context files will have the following folder/file structure `/config_contexts/<filter>/<slug>.[json|yaml]`, in which case their path and filename will be taken as an implicit scope for the context. For example:

```shell
config_contexts/
  regions/
    nyc.yaml       # YAML data, with implicit scoping to the Region with slug "nyc"
  sites/
    nyc-01.json    # JSON data, with implicit scoping to the Site with slug "nyc-01"
```

The implicit config contexts will be defined using dictionaries for both `_metadata` and any context data for the config context.

##### JSON

```json
{
    "_metadata": {
        "name": "Region NYC servers",
        "weight": 1000,
        "description": "NTP and Syslog servers for region NYC",
        "is_active": true,
        "schema": "Config Context Schema 1"
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

##### YAML

```yaml
_metadata":
  name: "Region NYC servers"
  weight: 1000
  description: "NTP and Syslog servers for region NYC"
  is_active: true
  schema: "Config Context Schema 1"

ntp-servers:
  - 172.16.10.22
  - 172.16.10.33
syslog-servers:
  - 172.16.9.100
  - 172.16.9.101
```

This will create a config context with two keys: `ntp-servers` and `syslog-servers`.

#### Local Configuration Contexts

Files in a `config_contexts/devices/` and/or `config_contexts/virtual_machines/` directory will be used to populate "local" config context data for individual devices or virtual machines. For these files, the device/VM name will always be taken from the filename, and the data in the file will be used precisely as-is (there is no need, or support, for a `_metadata` key in these files).

```shell
config_contexts/
  devices/
    rtr-01.yaml    # YAML data, local to the Device named "rtr-01"
  virtual_machines/
    vm001.json     # JSON data, local to the VirtualMachine named "vm001"
```

!!! note
    While virtual machines are always uniquely identified by their name, it is possible for devices associated with different sites and/or tenants to share an identical name. Currently, Nautobot is unable to automatically apply local config context via Git to devices that have a non-globally-unique name (or no name at all).

### Configuration Context Schemas

Config context schemas may be provided as JSON or YAML files located in `/config_context_schemas/`.

Files in the root of the `/config_context_schemas/` directory will be imported as described below, with no special meaning attributed to their filenames (the name of the constructed config context schema will be taken from the `_metadata` within the file, not the filename). Similar to config context definitions, a single file may define a single config context schema or a list of such schemas - see examples below.

```shell
config_context_schemas/
  context_schema_1.json
  context_schema_2.yaml
```

When loading the schema, the key `_metadata` will be extracted from the loaded data and used to define the config context schema's metadata, while the actual config context data schema will be based on the key `data_schema`.

JSON single example:

```json
{
  "_metadata": {
    "name": "Config Context Schema 1",
    "description": "Schema for defining first names."
  },
  "data_schema": {
    "title": "Person",
    "properties": {
      "firstName": {
        "type": "string",
        "description": "The person's first name."
      }
    }
  }
}
```

JSON list example:

```json
[
  {
    "_metadata": {
      "name": "Config Context Schema 1",
      "description": "Schema for defining first names."
    },
    "data_schema": {
      "title": "Person",
      "properties": {
        "firstName": {
          "type": "string",
          "description": "The person's first name."
        },
      }
    }
  },
  {
    "_metadata": {
      "name": "Config Context Schema 2",
      "description": "Schema for defining last names."
    },
    "data_schema": {
      "title": "Person",
      "properties": {
        "lastName": {
          "type": "string",
          "description": "The person's last name."
        },
      }
    }
  },
]
```

YAML single example:

``` yaml
---
_metadata:
  name: "Config Context Schema 1"
  description: "Schema for defining first names."
data_schema:
  title: "Person"
  properties:
    firstName:
      type: "string"
      description: "The person's first name"
```

YAML list example:

```yaml
---
- _metadata:
    name: "Config Context Schema 1"
    description: "Schema for defining first names."
  data_schema:
    title: "Person"
    properties:
      firstName:
        type: "string"
        description: "The person's first name"
- _metadata:
    name: "Config Context Schema 2"
    description: "Schema for defining last names."
  data_schema:
    title: "Person"
    properties:
      lastName:
        type: "string"
        description: "The person's last name"
```

### Export Templates

Export templates may be provided as files located in `/export_templates/<grouping>/<model>/<template_file>`; for example, a JSON export template for Device records might be `/export_templates/dcim/device/mytemplate.json`.

* The name of a discovered export template will be presented in Nautobot as `<repository name>: <filename>`.
* The MIME type of a file rendered from a discovered export template will try to match the extension to [`IANA's list`](https://www.iana.org/assignments/media-types/media-types.xhtml). If not detected, it will default to `text/plain`.
* The file extension of a file rendered from a discovered export template will match that of the template itself (so, in the above example, the extension would be `.json`)
