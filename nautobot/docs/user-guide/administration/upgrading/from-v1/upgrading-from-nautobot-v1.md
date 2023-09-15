# Upgrading from Nautobot v1.X

## Pre-migration validation

In Nautobot 1.x, starting with 1.5.22, there is a `nautobot-server pre_migrate` command that can be run to check your existing data for compatibility with the data model changes introduced in Nautobot 2.0. You are highly encouraged to run this command before beginning to migrate to Nautobot 2.x as it will catch and report certain data-sanitization issues that cannot be remediated automatically during the migration and will need to be manually corrected before you upgrade.

For example, if any of the pre-migration checks fail, you may see an error message like this:

```no-highlight
$ nautobot-server pre_migrate
>>> Running check: check_configcontext_uniqueness...
>>> Running check: check_exporttemplate_uniqueness...
>>> Running check: check_virtualchassis_uniqueness...
CommandError: One or more pre-migration checks failed:
    You cannot migrate ConfigContext or ConfigContextSchema objects that have non-unique names:
    - ConfigContext: [{'name': 'cc1', 'count': 2}]
    - ConfigContextSchema: [{'name': 'ccs1', 'count': 2}]

    You cannot migrate VirtualChassis objects with non-unique names:
     - [{'name': 'vc1', 'count': 2}]
```

Otherwise, a clean exit displays "All pre-migration checks passed." indicating that your Nautobot instance is ready to be upgraded to Nautobot 2.0:

```no-highlight
$ nautobot-server pre_migrate
>>> Running check: check_configcontext_uniqueness...
>>> Running check: check_exporttemplate_uniqueness...
>>> Running check: check_virtualchassis_uniqueness...
All pre-migration checks passed.
```

### Permission Constraint Migration

Permission constraints that contain references to fields or models that were changed or removed in Nautobot 2.0 will have to be updated manually after the upgrade. For example, any permission constraints that reference a `Site` will need to be updated to reference the `Location` model instead. The `nautobot-server pre_migrate` command will output a list of all permission constraints that need to be updated after the upgrade.

```no-highlight
>>> Running permission constraint checks...

One or more permission constraints may be affected by the Nautobot 2.0 migration.
These permission constraints will have to be updated manually after upgrading to
Nautobot 2.0 to reference new models and/or values. Please review the following
warnings and make sure to document the objects referenced by these constraints
before upgrading:

ObjectPermission 'backbone devices' (id: ced686c3-2b34-4612-974a-bad766512661) has a constraint that references a model (nautobot.dcim.models.devices.DeviceRole) that will be migrated to a new model by the Nautobot 2.0 migration.
{
    "device_role": "e99adc77-40ef-4a0f-b2c1-26dbf6648ef1"
}

ObjectPermission 'example job run' (id: 41c6d03e-6388-47eb-b575-1c7a21725bc3) has a constraint that references a model field (nautobot.extras.models.jobs.Job.name) that may be changed by the Nautobot 2.0 migration.
{
    "name": "Example job, does nothing"
}

ObjectPermission 'emea' (id: 2d3b7aae-98ab-44ec-af89-43d3002a1b7d) has a constraint that references a model (nautobot.dcim.models.sites.Region) that will be migrated to a new model by the Nautobot 2.0 migration.
[
    {
        "site__region__slug": "emea"
    },
    {
        "id": "4c9f3e5c-2dc6-46f6-95ac-ac778369edfc"
    }
]
```

We recommend taking inventory of any objects referenced by primary key in permission constraints for the following models:

- `dcim.DeviceRole`
- `dcim.RackRole`
- `extras.TaggedItem`
- `ipam.Aggregate`
- `ipam.IPAddress`
- `ipam.Prefix`
- `ipam.Role`

This is because the primary key for these objects may be changed during the migration. You will not be able to use the primary key value from the old object in the constraint to find the new object.

!!! note
    This pre-migration check only checks the last model referenced in a constraint filter. If you have nested filters (`device_role__devices`) they may not be reported by this check. You should review all of your permission constraints after the upgrade to ensure that they are still valid.

#### Examples

Primary keys for the migrated `Site` and `Region` objects were retained in the `Location` model, so you do not need to update the primary key value in any `Site` or `Region` constraints:

```json title="Old Constraint"
{
    "site": "4c9f3e5c-2dc6-46f6-95ac-ac778369edfc"
}
```

```json title="New Constraint"
{
    "location": "4c9f3e5c-2dc6-46f6-95ac-ac778369edfc"
}
```

Other models such as the `DeviceRole` that was migrated to `Role` did not retain the original primary key. In this case you will need to find the new object's primary key and update the constraint to reference the new model and new primary key value:

```json title="Old Constraint"
{
    "device_role": "00000000-0000-0000-0000-000000000000"
}
```

```json title="New Constraint"
{
    "role": "11111111-1111-1111-1111-111111111111"
}
```

You may also need to update field names in your permission constraints. For example, if you have a permission constraint that references the `slug` field on a model that was removed in Nautobot 2.0, you will need to update the constraint to reference a different field instead:

```json title="Old Constraint"
{
    "slug": "router-01"
}
```

```json title="New Constraint"
{
    "id": "5f96ac85-32d4-435d-84e4-66e631ae133f"
}
```

Some fields were only renamed without making any changes to the data so the constraint update will be a simple matter of updating the field name:

```json title="Old Constraint"
{
    "circuit__type__name": "metro-ethernet-1000mb"
}
```

```json title="New Constraint"
{
    "circuit__circuit_type__name": "metro-ethernet-1000mb"
}
```

## Dependency Changes

- Nautobot no longer uses or supports the use of `django-cryptography`.
- Nautobot no longer uses or supports the use of `django-mptt`.
- Nautobot no longer uses or supports the use of `django-rq`.

## Database (ORM) Changes

### Database Field Behavior Changes

Most of the database field behavior changes in Nautobot 2.0 fall into the following general categories:

1. The `created` field on models has changed from a date only ("2023-04-06") to being a date/time ("2023-04-06T19:57:45.320232Z")
2. Various models that had a required `site` field and an optional `location` field now have a required `location` field.

??? info "Full table of database field behavior changes"
    {data-table user-guide/administration/upgrading/from-v1/tables/v2-database-behavior-changes.yaml}

### Renamed Database Fields

Most renamed database fields in Nautobot 2.0 fall into the following general categories:

1. Renaming of foreign keys and reverse relations to more consistently and specifically match the related model name or plural name (for example, `Circuit.terminations` to `Circuit.circuit_terminations`, `Rack.group` to `Rack.rack_group`)
2. Renaming of tree model fields for consistency and due to the change from `django-mptt` to `django-tree-queries` (for example, `InventoryItem.child_items` to `InventoryItem.children` and `InventoryItem.level` to `InventoryItem.tree_depth`)

??? info "Full table of renamed database fields"
    {data-table user-guide/administration/upgrading/from-v1/tables/v2-database-renamed-fields.yaml}

### Removed Database Fields

Most removed database fields in Nautobot 2.0 fall into the following general categories:

1. Removal of references to removed models such as `Site` and `Region`
2. Removal of `slug` fields in preference to the use of autogenerated composite keys.
3. Removal of `django-mptt` internal fields (`lft`, `rght`, `tree_id`)

??? info "Full table of removed database fields"
    {data-table user-guide/administration/upgrading/from-v1/tables/v2-database-removed-fields.yaml}

!!! info
    For more information on how to update your integrations after the removal of `slug` fields, see [Uniquely Identifying a Nautobot Object](../../../../development/apps/api/platform-features/uniquely-identify-objects.md).

### Replaced Models

#### Generic Role Model

The `ipam.Role`, `dcim.RackRole`, and `dcim.DeviceRole` models have been removed and replaced by a single `extras.Role` model. This means that any references to the removed models in the code now use the `extras.Role` model instead.

| Removed Model     | Replaced With  |
|-------------------|----------------|
| `dcim.DeviceRole` | `extras.Role`  |
| `dcim.RackRole`   | `extras.Role`  |
| `ipam.Role`       | `extras.Role`  |

#### Site and Region Models

The `dcim.Region` and `dcim.Site` models have been removed and replaced by `dcim.Location` model. This means that any references to the removed models in the code now use the `dcim.Location` model instead with `LocationType` "Site" and "Region".

!!! important
    If you are a Nautobot App developer, or have any Apps installed that include data models that reference `Site` or `Region`, please review the [Region and Site Related Data Model Migration Guide](./region-and-site-data-migration-guide.md#region-and-site-related-data-model-migration-guide-for-existing-nautobot-app-installations) to learn how to migrate your apps and models from `Site` and `Region` to `Location`.

| Removed Model     | Replaced With  |
|-------------------|----------------|
| `dcim.Region`     | `dcim.Location`|
| `dcim.Site`       | `dcim.Location`|

#### Aggregate Migrated to Prefix

The `ipam.Aggregate` model has been removed and all existing Aggregates will be migrated to `ipam.Prefix` records with their `type` set to "Container". The `Aggregate.date_added` field will be migrated to `Prefix.date_allocated` and changed from a Date field to a DateTime field with the time set to `00:00` UTC. `Aggregate.tenant`, `Aggregate.rir` and `Aggregate.description` will be migrated over to the equivalent fields on the new `Prefix`. ObjectChanges, Tags, Notes, Permissions, Custom Fields, Custom Links, Computed Fields and Relationships will be migrated to relate to the new `Prefix` as well.

If a `Prefix` already exists with the same network and prefix length as a previous `Aggregate`, the `rir` and `date_added` fields will be copied to the `rir` and `date_allocated` fields on the existing Prefix object. Messages will be output during migration (`nautobot-server migrate` or `nautobot-server post_upgrade`) if the `tenant`, `description` or `type` fields need to be manually migrated.

| Aggregate        | Prefix               |
|------------------|----------------------|
| `broadcast`      | `broadcast`          |
| **`date_added`** | **`date_allocated`** |
| `description`    | `description`        |
| `network`        | `network`            |
| `prefix_length`  | `prefix_length`      |
| `rir`            | `rir`                |
| `tenant`         | `tenant`             |

### Prefix Parenting Concrete Relationship

The `ipam.Prefix` model has been modified to have a self-referencing foreign key as the `parent` field. Parenting of prefixes is now automatically managed at the database level to greatly improve performance especially when calculating tree hierarchy and utilization.

As a result of this change, it is no longer necessary nor possible to disable tree hierarchy using `settings.DISABLE_PREFIX_LIST_HIERARCHY` as this setting has been removed. Additionally it is no longer possible to disable global uniqueness using `settings.ENFORCE_GLOBAL_UNIQUE` as this setting has been removed.

The following changes have been made to the `Prefix` model.

| Removed                | Replaced With   |
|------------------------|-----------------|
| `get_child_prefixes()` | `descendants()` |

#### Prefix Parenting Guidance

The following guidance has been added for the `Prefix` model in order to ensure more accurate network modeling:

- A `Prefix` of type `Container` should only have a parent (if any) of type `Container`
- A `Prefix` of type `Network` should only have a parent (if any) of type `Container`
- A `Prefix` of type `Pool` should only have a parent (if any) of type `Network`
- Any `Prefix` can be a root prefix (i.e. have no parent)

In Nautobot 2.0, creating or updating prefixes that violate this guidance will result in a warning; in a future Nautobot release this will be changed to an enforced data constraint.

### IPAddress Parenting Concrete Relationship

The `ipam.IPAddress` model has been modified to have a foreign key to `ipam.Prefix` as the `parent` field. Parenting of IP addresses is now automatically managed at the database level to greatly improve performance especially when calculating tree hierarchy and utilization.

#### IPAddress Parenting Guidance

The following guidance has been added to the `IPAddress` model:

- An `IPAddress` should have a parent `Prefix` of type `Network`
- An `IPAddress` should not be created if a suitable parent `Prefix` of type `Network` does not exist
- An `IPAddress` can be a member of a `Pool` but only if the `Pool` is a child of a `Network`

As with the [`Prefix` parenting guidance](#prefix-parenting-guidance) above, violating this guidance in Nautobot 2.0 will result in a warning; in a future Nautobot release this will be changed to an enforced data constraint.

### Prefix get_utilization Method

The `get_utilization` method on the `ipam.Prefix` model has been updated in 2.0 to account for the `Prefix.type` field. The behavior is now as follows:

- If the `Prefix.type` is `Container`, the utilization is calculated as the sum of the total address space of all child prefixes.
- If the `Prefix.type` is `Pool`, the utilization is calculated as the sum of the total number of IP addresses within the pool's range.
- If the `Prefix.type` is `Network`:
    - The utilization is calculated as the sum of the total address space of all child `Pool` prefixes plus the total number of child IP addresses.
    - For IPv4 networks larger than /31, if neither the first or last address is occupied by either a pool or an IP address, they are subtracted from the total size of the prefix.

#### Example

- 192.168.0.0/16          `Container - 1024/65536 utilization`
    - 192.168.1.0/24      `Network - 1/254 utilization`
        - 192.168.1.1     `IP Address`
    - 192.168.2.0/24      `Network - 4/256 utilization`
        - 192.168.2.0/30  `Pool - 1/4 utilization`
            - 192.168.2.1 `IP Address`
    - 192.168.3.0/24      `Network - 5/254 utilization`
        - 192.168.3.1     `IP Address`
        - 192.168.3.64/30 `Pool - 0/4 utilization`
    - 192.168.4.0/24      `Network - 1/256 utilization`
        - 192.168.4.255   `IP Address`

## GraphQL and REST API Changes

### API Behavior Changes

Most of the API behavior changes in Nautobot 2.0 fall into the following general categories:

1. The `created` field on most models has changed from a date only ("2023-04-06") to being a date/time ("2023-04-06T19:57:45.320232Z")
2. The `status` fields on various models has changed from a pseudo-enum value (containing a "value" and a "label") to referencing the related Status object in full, similar to other foreign-key fields.
3. Various models that had a required `site` field and an optional `location` field now have a required `location` field.

??? info "Full table of API behavior changes"
    {data-table user-guide/administration/upgrading/from-v1/tables/v2-api-behavior-changes.yaml}

### Renamed Serializer Fields

Most renamed API fields in Nautobot 2.0 fall into the following general categories:

1. Renaming of foreign keys and reverse relations to more consistently and specifically match the related model name or plural name (for example, `Circuit.type` to `Circuit.circuit_type`, `Interface.count_ipaddresses` to `Interface.ip_address_count`)
2. Renaming of tree model fields for consistency and due to the change from `django-mptt` to `django-tree-queries` (for example, `InventoryItem._depth` to `InventoryItem.tree_depth`)

??? info "Full table of renamed API fields"
    {data-table user-guide/administration/upgrading/from-v1/tables/v2-api-renamed-fields.yaml}

### Removed Serializer Fields

Most removed database fields in Nautobot 2.0 fall into the following general categories:

1. Removal of references to removed models such as `Site` and `Region`
2. Removal of `slug` fields in preference to the use of autogenerated composite keys.

??? info "Full table of removed API fields"
    {data-table user-guide/administration/upgrading/from-v1/tables/v2-api-removed-fields.yaml}

### Removed 1.X Version Endpoints and Serializer Representations

Nautobot 2.0 removes support for 1.X versioned REST APIs and their Serializers. Requesting [older API versions](../../../platform-functionality/rest-api/overview.md#versioning) will result in a `400 Bad Request` error.

Please ensure you are using the latest representations of request/response representations as seen in the API docs or Swagger.

### Replaced Endpoints

These endpoints `/ipam/roles/`, `/dcim/rack-roles/` and `/dcim/device-roles/` are no longer available. Instead,  use the `/extras/roles/` endpoint to retrieve and manipulate `role` data.

| Removed Endpoints     | Replaced With    |
|-----------------------|------------------|
| `/dcim/device-roles/` | `/extras/roles/` |
| `/dcim/rack-roles/`   | `/extras/roles/` |
| `/ipam/roles/`        | `/extras/roles/` |

### New Interface to IP Address Relationship Endpoint

The through table (`ipam.IPAddressToInterface`) for the `IPAddress` to `Interface`/`VMInterface` many-to-many relationship has been exposed through the REST API at `/api/ipam/ip-address-to-interface/`. This endpoint must be used to create, retrieve, update, and delete relationships between IP addresses and interfaces through the REST API. Each `ipam.IPAddressToInterface` object maps a single `ipam.IPAddress` object to a single `dcim.Interface` or `virtualization.VMInterface` object. When creating relationships through this endpoint, the `ip_address` field is required and one of `interface` or `vm_interface` is required. There are additional boolean fields (`is_primary`, `is_default`, etc.) exposed through the REST API that may be used if desired but are not currently implemented in the Nautobot UI.

### API Query Parameters Changes

Nautobot 2.0 removes the `?brief` query parameter and adds support for the `?depth` query parameter. As a result, the ability to specify `brief_mode` in `DynamicModelChoiceField`, `DynamicModelMultipleChoiceField`, and `MultiMatchModelMultipleChoiceField` has also been removed. For every occurrence of the aforementioned fields where you have `brief_mode` set to `True/False` (e.g. `brief_mode=True`), please remove the statement, leaving other occurrences of the fields where you do not have `brief_mode` specified as they are.
Please see the [documentation on the `?depth` query parameter](../../../platform-functionality/rest-api/overview.md#depth-query-parameter) for more information.

## UI, GraphQL, and REST API Filter Changes

!!! note
    These sweeping changes made to model filter fields will, in some cases, invalidate existing `DynamicGroup` instances' filter data. Please utilize the [`nautobot-server audit_dynamic_groups`](../../tools/nautobot-server.md#audit_dynamic_groups) helper command when you are cleaning up `DynamicGroup` filter data. You should run this command after your Nautobot instance is upgraded to v2.x successfully.

### Removed Changelog URL from View Context

`changelog_url` is no longer provided in the `ObjectView` context. To get a model instance's changelog URL, you can retrieve it from the instance itself if it supports it: `model_instance.get_changelog_url()`.

### Renamed Filter Fields

Most renamed filter fields in Nautobot 2.0 fall into the following general categories:

1. The `tag` filter is renamed to `tags` on all models supporting Tags.
2. Renames to match renamed model/serializer fields as described earlier in this document.
3. Related membership filters are renamed to `has_<related>` throughout, for example `ConsolePort.cabled` is renamed to `ConsolePort.has_cable`.
4. Most `<related>_id` filters have been merged into the corresponding `<related>` filter (see ["Enhanced Filter Fields"](#enhanced-filter-fields) below).

??? info "Full table of renamed filter fields"
    {data-table user-guide/administration/upgrading/from-v1/tables/v2-filters-renamed-fields.yaml}

### Enhanced Filter Fields

Below is a table documenting [enhanced filter field changes](../../../../release-notes/version-2.0.md#enhanced-filter-fields-2804) in Nautobot 2.0. These enhancements mostly fall into the following general categories:

1. Many filters are enhanced to permit filtering by UUID _or_ by name.
2. Filters that previously only supported a single filter value can now filter on multiple values.

??? info "Full table of enhanced filter fields"
    {data-table user-guide/administration/upgrading/from-v1/tables/v2-filters-enhanced-fields.yaml}

### Corrected Filter Fields

Below is a table documenting [corrected filter field changes](../../../../release-notes/version-2.0.md#corrected-filter-fields-2804) in Nautobot 2.0. These corrections mostly involve filters that previously permitted filtering on related membership only (`/api/dcim/devices/?console_ports=True`) and have now been corrected into filters for related membership (`/api/dcim/devices/?has_console_ports=True`) as well as by actual related objects (`/api/dcim/devices/?console_ports=<UUID>`).

??? info "Full table of corrected filter fields"
    {data-table user-guide/administration/upgrading/from-v1/tables/v2-filters-corrected-fields.yaml}

### Removed Filter Fields

Below is a table documenting [removed filter field changes](../../../../release-notes/version-2.0.md#removed-filter-fields-2804) in v2.x.
Most removed database fields in Nautobot 2.0 fall into the following general categories:

1. Removal of `*_id=<uuid>` filters as they have have been merged into filters that support both uuid and name/slug (for example, instead of `/api/circuits/circuits/?provider_id=<UUID>`, use `/api/circuits/circuits/?provider=<uuid>`).
2. Removal of filtering on removed models such as `Region` and `Site`. (Use `location` filters instead.)
3. Removal of `slug` filters from models that no longer have a `slug` field.

??? info "Full table of removed filter fields"
    {data-table user-guide/administration/upgrading/from-v1/tables/v2-filters-removed-fields.yaml}

## Python Code Location Changes

The below is mostly relevant only to authors of Jobs and Nautobot Apps. End users should not be impacted by the changes in this section. Most changes in code location arise from the merging of the `nautobot.utilities` module into the `nautobot.core` module.

??? info "Full table of code location changes"
    {data-table user-guide/administration/upgrading/from-v1/tables/v2-code-location-changes.yaml}

## Removed Python Code

- Because of the replacement of the `?brief` REST API query parameter with `?depth` and the removal of all `Nested*Serializers`, some of the classes and mixins are removed because they are no longer needed.
- In the redesigned UI of Nautobot 2.0, menu items may no longer contain buttons, and so the `NavMenuButton` class and its subclasses have been removed as they are no longer needed/supported.
- With the reimplementation of CSV import and export, `CSVForm` classes are generally no longer needed, and so a number of mixins have been removed.

??? info "Full table of code removals"
    {data-table user-guide/administration/upgrading/from-v1/tables/v2-code-removals.yaml}

## Renamed Python Code

The below is mostly relevant only to authors of Jobs and Nautobot Apps. End users should not be impacted by the changes in this section. Most of the code renames are only relevant to Job related classes.

??? info "Full table of code renames"
    {data-table user-guide/administration/upgrading/from-v1/tables/v2-code-renames.yaml}

## Git Data Source Changes

The Configuration Contexts Metadata key `schema` has been replaced with `config_context_schema`. This means that any `schema` references in your git repository's data must be updated to reflect this change.

`GitRepository` sync operations are now Jobs. As a result, when creating a new `GitRepository` it **is not automatically synchronized**. A `GitRepository.sync()` method has been implemented that will execute the sync job on a worker and return the `JobResult` for the operation. This method takes `dry_run` and `user` arguments. The `dry_run` argument defaults to `False`; if set to `True` will cause the sync to dry-run. The `user` argument is required if a sync is performed.

Additionally, the `GitRepository.save()` method no longer takes a `trigger_resync=<True|False>` argument as it is no longer required. The act of creating a new `GitRepository` no longer has side effects.

Below is a table documenting changes in names for Git-related Jobs. There should NOT be a need to ever manually execute the jobs due to the addition of `GitRepository.sync()`, but this is being provided for clarity.

| Old Job Location                                                       | New Job Location                         |
|------------------------------------------------------------------------|------------------------------------------|
| `nautobot.extras.datasources.git.pull_git_repository_and_refresh_data` | `nautobot.core.jobs.GitRepositorySync`   |
| `nautobot.extras.datasources.git.git_repository_diff_origin_and_local` | `nautobot.core.jobs.GitRepositoryDryRun` |

## Logging Changes

Where applicable, `logging.getLogger("some_arbitrary_name")` is replaced with `logging.getLogger(__name__)` or `logging.getLogger(__name__ + ".SpecificFeature")`.

Below is a table documenting changes in logger names that could potentially affect existing deployments with expectations around specific logger names used for specific purposes.

??? info "Full table of logger name changes"
    {data-table user-guide/administration/upgrading/from-v1/tables/v2-logging-renamed-loggers.yaml}

## Job Database Model Changes

The Job `name` field has been changed to a unique field and the `name` + `grouping` uniqueness constraint has been removed. The processes that refresh jobs (`nautobot-server post_upgrade` and `nautobot-server migrate`) have been updated to gracefully handle duplicate job names.

!!! example
    ```py
    class NautobotJob1(Job):
        class Meta:
            name = "Sample job"

    class NautobotJob2(Job):
        class Meta:
            name = "Sample job"
    ```

    These jobs would be named `Sample job` and `Sample job (2)`

The Job `slug`, `source` and `git_repository` fields have been removed. The Job `module_name` field will automatically be updated, for Jobs derived from a Git repository, from `<submodule_name>` to `<git_repository_slug>.jobs.<submodule_name>`. This also changes the secondary uniqueness constraint for Jobs to simply `[module_name, job_class_name]`.

The Job `class_path` attribute has been simplified correspondingly, to simply `<module>.<ClassName>` instead of the former `<source>/<module>/<ClassName>`. For example, the Nautobot Golden Config backup job's `class_path` will change from `plugins/nautobot_golden_config.jobs/BackupJob` to `nautobot_golden_config.jobs.BackupJob`.

The Job `commit_default` field has been renamed to `dryrun_default` and the default value has been changed from `True` to `False`. This change is a result of the fundamental job changes mentioned in the [Job Changes](#job-changes) section below.

## JobResult Database Model Changes

The `JobResult` objects for which results from Job executions are stored are now automatically managed. Therefore job authors must never manipulate or `save()` these objects as they are now used internally for all state transitions and saving the objects yourself could interfere with and cause Job execution to fail or cause data loss.

Therefore all code that is calling `JobResult.set_status()` (which has been removed) or `JobResult.save()` must be removed.

## Job Changes

### Migrating Jobs From v1 to v2

+/- 2.0.0
    See [Migrating Jobs From Nautobot v1](../../../../development/jobs/migration/from-v1.md) for more information on how to migrate your existing jobs to Nautobot v2.

### Fundamental Changes

The `BaseJob` class is now a subclass of Celery's `Task` class. Some fundamental changes to the job's methods and signatures were required to support this change:

- The `test_*` and `post_run` methods for backwards compatibility to NetBox scripts and reports were removed. Celery implements `before_start`, `on_success`, `on_retry`, `on_failure`, and `after_return` methods that can be used by job authors to perform similar functions.

!!! important
    Be sure to call the `super()` method when overloading any of the job's `before_start`, `on_success`, `on_retry`, `on_failure`, or `after_return` methods

- The run method signature is now customizable by the job author. This means that the `data` and `commit` arguments are no longer passed to the job by default and the job's run method signature should match the the job's input variables.

!!! example
    ```py
    class ExampleJob(Job):
        var1 = StringVar()
        var2 = IntegerVar(required=True)
        var3 = BooleanVar()
        var4 = ObjectVar(model=Role)

        def run(self, var1, var2, var3, var4):
            ...
    ```

### Database Transactions

Nautobot no longer wraps the job `run` method in an atomic database transaction. As a result, jobs that need to roll back database changes will have to decorate the run method with `@transaction.atomic` or use the `with transaction.atomic()` context manager in the job code.

With the removal of the atomic transaction, the `commit` flag has been removed. The ability to bypass job approval on dryrun can be achieved by using an optional `dryrun` argument. Job authors who wish to allow users to bypass approval when the `dryrun` flag is set should set a `dryrun` attribute with a value of `DryRunVar()` on their job class. `DryRunVar` can be imported from `nautobot.extras.jobs`.

!!! example
    ```py
    from nautobot.extras.jobs import DryRunVar, Job

    class ExampleJob(Job):
        dryrun = DryRunVar()

        def run(self, dryrun):
            ...
    ```

A new `supports_dryrun` field has been added to the `Job` model and `Job` class that returns true if the `Job` class implements the `dryrun = DryRunVar()` attribute. This is used to determine if jobs that require approval can be dry run without prior approval.

The `commit_default` job field has been renamed to `dryrun_default` and the default value has been changed from `True` to `False`.

!!! important
    The `read_only` job field no longer changes the behavior of Nautobot core and is left to the job author to decide whether their job is read only.

!!! important
    Nautobot no longer enforces any job behavior when dryrun is set. It is now the job author's responsibility to define and enforce the execution of a "dry run".

### Request Property

The `request` property has been changed to a Celery request instead of a Django web request and no longer includes the information from the web request that initiated the Job. The `user` object is now available as `self.user` instead of `self.request.user`.

### URL Changes

The Job URL path `jobs/results/<uuid:pk>/` and URL pattern name `job_jobresult` are removed. Use URL path `job-results/<uuid:pk>/` and URL pattern name `jobresult` instead. Any `extras:job_jobresult` references should be removed and be replaced by `extras:jobresult`.

The Job URL path `/extras/jobs/<str:class_path>/` and associated URL pattern name `extras:job` are changed to URL path `/extras/jobs/<str:class_path>/run/` and the URL pattern is renamed to `extras:job_run_by_class_path`. Conversely, the Job detail view URL pattern name `extras:job_detail` has been renamed to `extras:job` for consistency with other object detail view URL patterns.

### Function Changes

Changed `as_form_class`, `as_form` and `validate_data` functions on `BaseJob` Model to `classmethods` so that they can be called directly from the class without needing to instantiate the Job in order to access them.

### Function Renames

`JobDetailView` is renamed to `JobView`.

`JobView` is renamed to `JobRunView`.

## Settings Changes

### Added Settings

These settings are new in Nautobot 2.0 and can be changed in your `nautobot_config.py` file or via environment variables if desired:

- [`CELERY_WORKER_REDIRECT_STDOUTS` (env: `NAUTOBOT_CELERY_WORKER_REDIRECT_STDOUTS`)](../../configuration/optional-settings.md#celery_worker_redirect_stdouts)
- [`CELERY_WORKER_REDIRECT_STDOUTS_LEVEL` (env: `NAUTOBOT_CELERY_WORKER_REDIRECT_STDOUTS_LEVEL`)](../../configuration/optional-settings.md#celery_worker_redirect_stdouts_level)

### Removed Settings

These settings are no longer in use and should be removed from your `nautobot_config.py` file and environment variables if present:

- `CACHEOPS_DEFAULTS` (env: `NAUTOBOT_CACHEOPS_TIMEOUT`)
- `CACHEOPS_ENABLED` (env: `NAUTOBOT_CACHEOPS_ENABLED`)
- `CACHEOPS_HEALTH_CHECK_ENABLED`
- `CACHEOPS_REDIS` (env: `NAUTOBOT_CACHEOPS_REDIS`)
- `CACHEOPS_SENTINEL`
- `DISABLE_PREFIX_LIST_HIERARCHY`
- `ENFORCE_GLOBAL_UNIQUE` (env: `NAUTOBOT_ENFORCE_GLOBAL_UNIQUE`)
- `RQ_QUEUES`

### Changed Settings

These settings are no longer user servicable and should be removed from your `nautobot_config.py` file and environment variables if present:

- `CELERY_RESULT_BACKEND` (env: `NAUTOBOT_CELERY_RESULT_BACKEND`)
- `CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS`
