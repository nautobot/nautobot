# Git Repositories

Some text-based content is more conveniently stored in a separate Git repository rather than internally in the Nautobot database. Nautobot offers the [Git as a Data Source](../feature-guides/git-data-source.md) feature for this use case. Such a repository may currently include any or all of the following for Nautobot to consume:

* Job source files and associated data files
* Configuration context data
* Export templates
* Additional data types as registered by any installed Apps

!!! important
    Nautobot's Git integration depends on the availability of the `git` program. If `git` is not installed, Nautobot will be unable to pull data from Git repositories.


## Repository Configuration

When defining a Git repository for Nautobot to consume, the `name`, `remote URL`, and `branch` parameters are mandatory - the name acts as a unique identifier, and the remote URL and branch are needed for Nautobot to be able to locate and access the specified repository. Additionally, if the repository is private you may specify a `secrets group` that can be used to gain access to the repository.

!!! note
    Nautobot currently only supports repositories that can be cloned using the standard git command line, `git clone`. This means App-style integrations like GitHub Apps are not currently supported, as their workflow of managing files leverages a REST API.

--- 2.0.0
    In Nautobot 1.x it was possible to configure the secrets (`username` and/or `token`) for a private Git Repository directly in Nautobot's database. Due to security concerns and maintainability challenges, this option has been removed. To access a private Git repository you now must use Secrets Groups.

The implementation of private repository access can vary from Git provider to Git provider. The following providers have been confirmed to work; in theory, additional providers using the same pattern will work, but there is currently no specific support for all providers.

* GitHub's [`token`](https://docs.github.com/en/free-pro-team@latest/github/authenticating-to-github/creating-a-personal-access-token) does not require a `username`.
* GitLab's [`token`](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html) requires a `username`, conventions are to use the username "oauth2". In addition, GitLab's [deploy tokens](https://docs.gitlab.com/ee/user/project/deploy_tokens/) are also supported.
* For Bitbucket, there are two options: [personal access tokens](https://confluence.atlassian.com/bitbucketserver/personal-access-tokens-939515499.html) or [OAuth2](https://developer.atlassian.com/cloud/bitbucket/oauth-2/) depending on the product.

!!! note
    When defining a [secrets group](./secret.md#secrets-groups) for a Git repository, the group must contain assigned secret(s) with an *access type* of `HTTP(S)` and *secret type(s)* of `Token` (and `Username`, if required by the provider).

Whenever a Git repository record is created, updated, or deleted, Nautobot automatically enqueues a background task that will asynchronously execute to clone, fetch, or delete a local copy of the Git repository on the filesystem (located under [`GIT_ROOT`](../administration/configuration/settings.md#git_root)) and then create, update, and/or delete any database records managed by this repository. The progress and eventual outcome of this background task are recorded as a `JobResult` record that may be viewed from the Git repository user interface.

!!! important
    The repository branch must exist and have a commit against it. At this time, Nautobot will not initialize an empty repository.

!!! note
    If you are using a self-signed Git repository, you will need to set the environment variable `GIT_SSL_NO_VERIFY="1"`
    in order for the repository to sync.

## Repository Structure

### Jobs

Jobs can be defined in Python files located in a `/jobs/` directory or `jobs.py` at the root of a Git repository. Any job classes defined in these files that have been registered during import will be discovered by Nautobot and made available to be run as a job. See the section on [Job registration](../../development/jobs/index.md#job-registration) for more information.

!!! note
    There **must** be an `__init__.py` file in the `/jobs/` directory.

+/- 2.0.0
    Jobs provided by a Git repository are loaded as real Python modules and now support inter-module relative Python imports (i.e., you can package Python "libraries" into a Git repository and then import them from Jobs in that repository). As a result, the top-level directory of Git repositories that provide jobs must now contain an `__init__.py` file.

When syncing or re-syncing a Git repository, the Nautobot database records corresponding to any provided jobs will automatically be refreshed. If a job is removed as a result of the sync, the corresponding database record will *not* be automatically deleted, but will be marked as `installed = False` and will no longer be runnable. A user with appropriate access permissions can delete leftover `Job` database records if desired, but note that this will result in any existing `JobResult` records no longer having a direct reference back to the `Job` that they originated from.

### Configuration Contexts

Config contexts may be provided as JSON or YAML files located in `/config_contexts/`. There are three different types of config context scopes; **explicit**, **implicit**, and **local**.

* **Explicit**: Defined as JSON or YAML files at the root of the `/config_contexts/` folder. Multiple config contexts can be specified within the each file. The metadata regarding the naming and scoping of the config context is determined by the `_metadata` key for each list element.
* **Implicit**: They're defined using a specific folder and file structure to apply the config context to a specific scope.
* **Local**: Defined at the device/virtual machine level and only being applied to the specific device/virtual machine.


#### Metadata

The metadata used to create the config context has the following options and is specified by the `_metadata` key.

| Key                    | Required | Default | Description                                                                       |
|------------------------| -------- | ------- | --------------------------------------------------------------------------------- |
| name                   | True     | N/A     | The name that will be assigned to the Config Context                              |
| weight                 | False    | 1000    | The weight that will be assigned to the Config Context that determines precedence |
| description            | False    | N/A     | The description applied to the Config Context                                     |
| is_active              | False    | True    | Whether or not the Config Context is active                                       |
| config_context_schema  | False    | N/A     | Config Context Schema that it should be validated against                         |

+/- 2.0.0
    The key for specifying Config Context Schemas was renamed from `schema` to `config_context_schema`.

There are several other keys that can be defined that match the scope of what the Config Context will be assigned to.

Here is an example `_metadata` key defined:

```json
{
    "_metadata": {
        "name": "Location NYC servers",
        "weight": 1000,
        "description": "NTP and Syslog servers for location NYC",
        "is_active": true,
        "locations": [{"name": "NYC"}],
        "config_context_schema": "Config Context Schema 1"
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
      - name: "Router"
  hostname_pattern_string: "rtr-.+"
- _metadata:
    name: "Console Server hostname pattern"
    roles:
      - name: "Console Server"
  hostname_pattern_string: "cs-.+"
- _metadata:
    name: "Switches hostname pattern"
    roles:
      - name: "Aggregation Switch"
      - name: "Services Switch"
  hostname_pattern_string: "switch-.+"
- _metadata:
    name: "Appliance hostname pattern"
    roles:
      - name: "Security Appliance"
  hostname_pattern_string: "fw-.+"
...
```

The `_metadata` key will map to the attributes required when creating a config context via the UI or API such as name and the scope of the config context. If we take a look at the first element, the name assigned to the config context will be `"Router hostname pattern"` and be scoped to `roles` with a name of `Router`.

Any key/value pair defined at the same level as `_metadata` will be converted to the config context data. Keeping with the first element, it will have a key set as `hostname_pattern_string` with a value of `rtr-.+`.

#### Implicit Config Contexts

Implicit config context files will have the following folder/file structure `/config_contexts/<filter>/<name>.[json|yaml]`, in which case their path and filename will be taken as an implicit scope for the context. For example:

```shell
config_contexts/
  locations/
    NYC.yaml       # YAML data, with implicit scoping to the Location with name "NYC"
    NYC 01.json    # JSON data, with implicit scoping to the Location with name "NYC 01"
```

+/- 2.0.0
    In Nautobot 1.x, the filenames were interpreted as `slug` strings for the related objects. In Nautobot 2.0 and later, the filenames are based on the `name` (or for `device-types` files, the `model`) of the related object instead.

The implicit config contexts will be defined using dictionaries for both `_metadata` and any context data for the config context.

##### JSON

```json
{
    "_metadata": {
        "name": "Region NYC servers",
        "weight": 1000,
        "description": "NTP and Syslog servers for region NYC",
        "is_active": true,
        "config_context_schema": "Config Context Schema 1"
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
  config_context_schema: "Config Context Schema 1"

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
    While virtual machines are always uniquely identified by their name, it is possible for devices associated with different locations and/or tenants to share an identical name. Currently, Nautobot is unable to automatically apply local config context via Git to devices that have a non-globally-unique name (or no name at all).

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

## Manage Git Repositories via the Nautobot REST API

Like other Nautobot features, Git repositories can be managed via [Nautobot's REST API](./rest-api/overview.md). The following is a non-exhaustive list of examples.

### Define a Git Repository to Consume

To use the Nautobot REST API to define a Git repository for Nautobot to consume, issue a `POST` request to the model's *list* endpoint with JSON data pertaining to the object being created. Note that a REST API token is required for all operations; see the [authentication documentation](./rest-api/authentication.md) for more information. Also be sure to set the `Content-Type` HTTP header to `application/json`. As always, it's a good practice to also set the `Accept` HTTP header to include the requested REST API version, so all of these examples will do that too:

```no-highlight
curl -s -X POST \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=2.4" \
http://nautobot/api/extras/git-repositories/ \
--data '{"name": "demo-git-datasource", "provided_contents": ["extras.configcontext", "extras.job", "extras.exporttemplate", "extras.configcontextschema"], "remote_url": "https://github.com/nautobot/demo-git-datasource.git"}' | jq '.'
```

!!! note
    The GUI automatically guides the user into issuing a sync or dry run automatically when defining a Git repository for Nautobot to consume, but when using the API it is necessary to issue the sync yourself if you wish to, as described [below](#trigger-a-sync-or-resync-of-a-defined-repository).

### List Existing Repositories

Just like other Nautobot apps and models, it is possible to use the Nautobot REST API to list existing configured repositories by issuing a `GET` request to the model's *list* endpoint. As usual, objects are listed under the response object's `results` parameter:

```no-highlight
curl -s -X GET \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=2.4" \
http://nautobot/api/extras/git-repositories/ | jq '.'
```

### Describe a Specific Existing Repository

If you have the `id` of a specific record from a previous `GET` operation or elsewhere, you can return the specific details for the record with a `GET` request referencing the specific `id`:

```no-highlight
curl -s -X GET \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=2.4" \
http://nautobot/api/extras/git-repositories/2ecb8556-db58-466d-8278-860b8fd74627/ | jq '.'
```

Returns, for example:

```json
{
  "id": "2ecb8556-db58-466d-8278-860b8fd74627",
  "object_type": "extras.gitrepository",
  "display": "demo-git-datasource",
  "url": "http://nautobot/api/extras/git-repositories/2ecb8556-db58-466d-8278-860b8fd74627/",
  "natural_slug": "demo-git-datasource_2ecb",
  "provided_contents": [
    "extras.configcontext",
    "extras.job",
    "extras.exporttemplate",
    "extras.configcontextschema"
  ],
  "name": "demo-git-datasource",
  "slug": "demo_git_datasource",
  "remote_url": "https://github.com/nautobot/demo-git-datasource.git",
  "branch": "main",
  "current_head": "939ea1ed854e405b600d70f798804eb2da356231",
  "secrets_group": null,
  "created": "2025-01-21T12:17:24.945117Z",
  "last_updated": "2025-01-21T12:17:30.081417Z",
  "notes_url": "http://nautobot/api/extras/git-repositories/2ecb8556-db58-466d-8278-860b8fd74627/notes/",
  "custom_fields": {},
  "tags": []
}
```

!!! note
    By design and like other secrets in Nautobot, the tokens used for a Git repository are never retrievable via a REST API request.

### Trigger a Sync or Resync of a Defined Repository

As noted previously, a newly defined Git repository will not automatically sync immediately, so if you want it to sync or resync you can issue a `POST` request to the specific `id` followed by `/sync/` like this:

```no-highlight
curl -s -X POST \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=2.4" \
http://nautobot/api/extras/git-repositories/2ecb8556-db58-466d-8278-860b8fd74627/sync/ | jq '.'
```

Which returns, for example:

```no-highlight
{
  "message": "Repository demo-git-datasource sync job added to queue.",
  "job_result": {
    "id": "68500ca5-27c3-488c-a24a-e98858bf52a1",
    "object_type": "extras.jobresult",
    "display": "Git Repository: Sync started at 2025-01-30 19:35:14.120625+00:00 (PENDING)",
    "url": "http://nautobot/api/extras/job-results/68500ca5-27c3-488c-a24a-e98858bf52a1/",
    "natural_slug": "68500ca5-27c3-488c-a24a-e98858bf52a1_6850",
    "status": {
      "value": "PENDING",
      "label": "PENDING"
    },
    "name": "Git Repository: Sync",
    "task_name": null,
    "date_created": "2025-01-30T19:35:14.120625Z",
    "date_done": null,
    "result": null,
    "worker": null,
    "task_args": [],
    "task_kwargs": {},
    "celery_kwargs": {},
    "traceback": null,
    "meta": null,
    "job_model": {
      "id": "ad2b27c8-adf0-4e23-a4d3-a37fe3c42abd",
      "object_type": "extras.job",
      "url": "http://nautobot/api/extras/jobs/ad2b27c8-adf0-4e23-a4d3-a37fe3c42abd/"
    },
    "user": {
      "id": "569138fe-f0b9-4abf-9812-c85a7ec73bbd",
      "object_type": "users.user",
      "url": "http://nautobot/api/users/users/569138fe-f0b9-4abf-9812-c85a7ec73bbd/"
    },
    "scheduled_job": null,
    "custom_fields": {},
    "computed_fields": {},
    "files": []
  }
}
```

### Query the Data Handled by a Defined Repository

It's even possible to query the API to discover resource types that have been created and managed by a specific repository. For example, this `GET` query on the `jobs` model's *list* endpoint is filtered through a `module_name__isw=demo_git_datasource` [query filter](./rest-api/filtering.md#string-fields) to identify those jobs that were created from the `demo-git-datasource` Git repository:

```no-highlight
curl -s -X GET \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=2.4" \
http://nautobot/api/extras/jobs/?module_name__isw=demo_git_datasource. | jq '.'
```

Here are the first 20 lines of JSON returned:

```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "f10b944f-184d-4b54-bb14-57f139f15ece",
      "object_type": "extras.job",
      "display": "Verify Circuit Termination",
      "url": "http://nautobot/api/extras/jobs/f10b944f-184d-4b54-bb14-57f139f15ece/",
      "natural_slug": "demo-git-datasource-jobs-data-quality_verifycircuittermination_f10b",
      "task_queues": [
        "default"
      ],
      "task_queues_override": false,
      "module_name": "demo_git_datasource.jobs.data_quality",
      "job_class_name": "VerifyCircuitTermination",
      "grouping": "Data Quality",
      "name": "Verify Circuit Termination",
      "description": "Verify a circuit has termination and an IP address",
```

Another way to approach the same goal would be to `GET` the full list and filter it through `jq` to identify those same jobs. The output is structured slightly differently but the results are broadly similar:

```no-highlight
curl -s -X GET \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=2.4" \
http://nautobot/api/extras/jobs/ | jq '.results[] | select(.natural_slug | startswith("demo-git-datasource"))'
```

Here are the first 20 lines for that one:

```json
{
  "id": "f10b944f-184d-4b54-bb14-57f139f15ece",
  "object_type": "extras.job",
  "display": "Verify Circuit Termination",
  "url": "http://nautobot/api/extras/jobs/f10b944f-184d-4b54-bb14-57f139f15ece/",
  "natural_slug": "demo-git-datasource-jobs-data-quality_verifycircuittermination_f10b",
  "task_queues": [
    "default"
  ],
  "task_queues_override": false,
  "module_name": "demo_git_datasource.jobs.data_quality",
  "job_class_name": "VerifyCircuitTermination",
  "grouping": "Data Quality",
  "name": "Verify Circuit Termination",
  "description": "Verify a circuit has termination and an IP address",
  "installed": true,
  "enabled": false,
  "is_job_hook_receiver": false,
  "is_job_button_receiver": false,
  "has_sensitive_variables": true,
```

As another example, the API call below filters `Config Contexts` using an `owner_object_id=<id>` query filter and the `id` of the Git repository:

```no-highlight
curl -s -X GET \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=2.4" \
http://nautobot/api/extras/config-contexts/?owner_object_id=2ecb8556-db58-466d-8278-860b8fd74627 | jq '.'
```

Here's the first part of the output:

```json
{
  "count": 6,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "26fbde54-e74a-427e-9545-6dbd1ff57855",
      "object_type": "extras.configcontext",
      "display": "[demo-git-datasource] data-models",
      "url": "http://nautobot/api/extras/config-contexts/26fbde54-e74a-427e-9545-6dbd1ff57855/",
      "natural_slug": "data-models_26fb",
      "owner_content_type": "extras.gitrepository",
      "owner": {
        "id": "2ecb8556-db58-466d-8278-860b8fd74627",
        "object_type": "extras.gitrepository",
        "url": "http://nautobot/api/extras/git-repositories/2ecb8556-db58-466d-8278-860b8fd74627/"
      },
      "name": "data-models",
      "owner_object_id": "2ecb8556-db58-466d-8278-860b8fd74627",
      "weight": 1000,
```
