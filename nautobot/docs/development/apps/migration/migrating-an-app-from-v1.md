# Migration Guide to Upgrade an App from V1 to V2

## Model Updates

### Core

#### Replace the Usage of Slugs with Composite Keys

Slugs were used to identify unique objects in the database for various models in Nautobot v1.x and they are now replaced by Composite Keys. The `slug` field can be safely deleted as long as your models are derived from `BaseModel` that automatically supports the following [natural key](https://docs.djangoproject.com/en/3.2/topics/serialization#natural-keys) APIs. For a more comprehensive guideline on how Natural Keys/Composite Keys in Nautobot v2.0 works, please go to the [Natural Key documentation](../../core/natural-keys.md).

### DCIM

#### Replace Site and Region with Location Model

`Site` and `Region` Models are replaced by `Site` and `Region` `LocationTypes` and `Locations`. Your models and data that are associated with `Site` or `Region` via ForeignKey or ManyToMany relationships are now required to be migrated to `Locations`. Please go [here](region-and-site-to-location.md) for a comprehensive migration guide on how to migrate your data from `Site` and `Region` to `Location` and `LocationType`.

### Extras

#### Replace Role Related Models with Generic Role Model

Narrowly defined role models including `dcim.DeviceRole`, `dcim.RackRole` and `ipam.Role` are replaced by a generic `extras.Role` model. If any of your models are using the replaced role models, it is required for you to remove the `role` field from your model and add either `nautobot.extras.models.roles.RoleModelMixin` or `nautobot.extras.models.roles.RoleRequiredRoleModelMixin` to your model class definition. `RoleModelMixin` adds a nullable `role` field whereas `RoleRequiredRoleModelMixin` adds a required `role` field. Please go [here](../../core/role-internals.md) to check out how the `extras.Role` model works in v2.0.

#### Updates to Job and Job related models

##### Job Model Changes

See details about the fundamental changes to `Job` Model [here](../../../user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.md#job-database-model-changes)

##### Job Logging Changes

Job logging is now handled by a logger off the Job itself and has a function for each level to send the message (info, warning, debug, etc). There is no longer a `log_success` or `log_failure` function. Checkout the changes in detail [here](../../../user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.md#logging-changes)

##### JobResult Model Changes

`JobResult` no longer needs a `job_id`, `user`, or `obj_type` passed to it. It now needs a `name`, `task_name`, and a `worker`. See [here](../../../user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.md#jobresult-database-model-changes) for details.

#### Update CustomField, ComputedField, and Relationship

In accordance with the removal of `slug` field in Nautobot v2.0, `CustomField`, `ComputeField` and `Relationship`'s `slug` field is replaced by the `key` field which contains a GraphQL-safe string that is used exclusively in the API and GraphQL. Their `label` fields are now used for display purposes only in the UI. Please go to their respective documentations for more information [CustomField](../../../user-guide/feature-guides/custom-fields.md), [ComputedField](../../../user-guide/platform-functionality/computedfield.md), and [Relationship](../../../user-guide/feature-guides/relationships.md).

### IPAM

#### Replace Aggregate with Prefix

`Aggregate` models are removed in v2.0 and all existing `Aggregate` instances are migrated to `Prefix` with type set to "Container". So your models and data that are associated with `Aggregate` via ForeignKey or ManyToMany relationships are now required to be migrated to `Prefix`. Please go [here](../../../user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.md) for this change and its potential impact on other models.

#### Introduction of Namespace

A namespace groups together a set of related but distinct [VRFs](../../../user-guide/core-data-model/ipam/vrf.md), [prefixes](../../../user-guide/core-data-model/ipam/prefix.md), and [IP addresses](../../../user-guide/core-data-model/ipam/ipaddress.md). Within a given namespace, only a single record may exist for each distinct VRF, prefix, or IP address. Although such a record may be used in multiple locations within your network, such as a VRF being configured on multiple devices, or a virtual IP address being assigned to multiple interfaces or devices, it is fundamentally a single network object in these cases, and Nautobot models this data accordingly. Check out the model documentation [here](../../../user-guide/core-data-model/ipam/namespace.md)

#### Concrete Relationship between Prefix and IP Address

[IP addresses](../../../user-guide/core-data-model/ipam/ipaddress.md) now have a concrete relationship with its parent [Prefix](../../../user-guide/core-data-model/ipam/prefix.md). `IPAddress.parent` now refers to the parent prefix and `Prefix.ip_addresses` refers to the child ips.`

#### Concrete Relationship between Prefix and Self

[Prefixes](../../../user-guide/core-data-model/ipam/prefix.md) now has a concrete parent/child relationship with itself. `Prefix.parent` refers to its parent prefix and `Prefix.children` refers to all its child prefixes.

#### Convert Relationship Type between Prefix and VRF to Many to Many

[Prefixes](../../../user-guide/core-data-model/ipam/prefix.md) now no longer has a ForeignKey to [VRF](../../../user-guide/core-data-model/ipam/vrf.md). Instead, the Many to Many relationship is now defined on the VRF side as `VRF.prefixes`. VRF is no longer assigned to an IPAddress and is now on the parent Prefix. It is now a M2M relationship between the VRF and Prefix. VRF is also no longer a uniqueness constraint on the Prefix. Namespace is used instead. There is a default `Global` Namespace that all Prefixes are migrated into from 1.x.

## Code Updates

### Update Code Import Locations

Most changes in code location arise from the merging of the `nautobot.utilities` module into the `nautobot.core` module.

??? info "Full table of code location changes"
    {data-table user-guide/administration/upgrading/from-v1/tables/v2-code-location-changes.yaml}

### Replace PluginMenuItem with NavMenuItem

In your app's `navigation.py` file. If you are still using `PluginMenuItem` from `nautobot.extras.plugin`, you should replace those code with `NavMenuGroup`, `NavMenuItem`, and `NavMenuTab` from `nautobot.apps.ui`.

For example:

Before:

```python

    from nautobot.extras.plugins import PluginMenuItem

    menu_items = (
        PluginMenuItem(
            link="plugins:your_app:dashboard",
            link_text="Dashboard",
            permissions=["your_app.view_sync"],
        ),
        PluginMenuItem(
            link="plugins:your_app:sync_list",
            link_text="History",
            permissions=["your_app.view_sync"],
        ),
        PluginMenuItem(
            link="plugins:your_app:synclogentry_list",
            link_text="Logs",
            permissions=["your_app.view_synclogentry"],
        ),
    )

```

After:

```python

from nautobot.apps.ui import NavMenuGroup, NavMenuItem, NavMenuTab


items = [
    NavMenuItem(
        link="plugins:your_app:dashboard",
        name="Dashboard",
        permissions=["your_app.view_sync"],
    ),
    NavMenuItem(
        link="plugins:your_app:sync_list",
        name="History",
        permissions=["your_app.view_sync"],
    ),
    NavMenuItem(
        link="plugins:your_app:synclogentry_list",
        name="Logs",
        permissions=["your_app.view_synclogentry"],
    ),
]

menu_items = (
    NavMenuTab(
        name="Plugins",
        groups=(NavMenuGroup(name="Your App", weight=1000, items=tuple(items)),),
    ),
)

```

### Replace DjangoFilterBackend with NautobotFilterBackend

If your Custom `FilterBackend` class is derived from `DjangoFilterBackend`, you should replace `DjangoFilterBackend` with `NautobotFilterBackend`.

### Revamp Rest API Serializers

All `NestedSerializers` classes are removed from Nautobot v2.0. If any `NestedSerializers` exist for your models, you should just remove their class definitions and references. In addition, the `?brief=` API query parameter is replaced by `?depth=<0-10>`. As a result, the ability to specify `brief_mode` in `DynamicModelChoiceField`, `DynamicModelMultipleChoiceField`, and `MultiMatchModelMultipleChoiceField` has also been removed. For every occurrence of the aforementioned fields where you have `brief_mode` set to `True/False` (e.g. `brief_mode=True`), please remove the statement, leaving other occurrences of the fields where you do not have `brief_mode` specified as they are. Checkout our [API documentation](../../../user-guide/platform-functionality/rest-api/overview.md#depth-query-parameter) for this change.

After removing existing `NestedSerializers`, you can change the `fields` attribute in your serializers' `class Meta` to `__all__` and that will automatically include all the model's fields in the serializer. If you want to exclude certain fields of the model, you can specify a list of fields you want to display in the `fields` attribute instead.

Include all model attributes:

```python
class ExampleModelSerializer(NautobotModelSerializer):
    """Used for normal CRUD operations."""

    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:example_plugin-api:anotherexamplemodel-detail")

    class Meta:
        model = AnotherExampleModel
        fields = "__all__"
```

Include only specified model attributes:

```python
class ExampleModelSerializer(NautobotModelSerializer):
    """Used for normal CRUD operations."""

    url = serializers.HyperlinkedIdentityField(view_name="plugins-api:example_plugin-api:anotherexamplemodel-detail")

    class Meta:
        model = AnotherExampleModel
        # example_attribute_4 is not included in the serializer
        fields = ["url", "example_attribute_1", "example_attribute_2", "example_attribute_3"]
```

### Revamp CSV Import and Export

CSV Import for models are now done automatically via the Rest API. As a result of this change, `CSVForms` classes are no longer needed and should be deleted. In addition, `csv_headers` and `to_csv` attributes should be removed from your model definition. Check out our [release notes](../../../release-notes/version-2.0.md#revamped-csv-import-and-export-2569-3715) for this specific change.

## Dependency Updates

### Nautobot Version

Change your Nautobot to the latest/v2.0 release.

### Python Version

Python 3.7 support is dropped for Nautobot v2.0 and Python 3.8 is the minimum version for Nautobot and its apps.

### pylint-nautobot

pylint-nautobot is now a required dev-dependency. Make sure you add `pylint-nautobot = "*"` under `tool.poetry.dev-dependencies` section in your `pyproject.toml`.
