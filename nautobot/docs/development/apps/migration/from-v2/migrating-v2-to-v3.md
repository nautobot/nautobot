# Migration Path

In the previous section, we provided a high-level overview of the migration steps. This section contains detailed instructions for each step.

## UI Migrations

!!! tip
    You can safely skip this section if you do not have any custom apps or can run `nautobot-migrate-bootstrap-v3-to-v5 <path> --dry-run --check-python-files` against your custom app without any fixes suggested. Note that HTML in Python search algorithm is greedy and occasionally may output false positives.

Nautobot v3.0 introduces many modernizations and improvements to building user interfaces. Although we did our best to make the migration as smooth as possible for app developers, we were not able to avoid some of the **breaking changes**. Below is a list of guides explaining how to upgrade respective UI parts.

Overall, there are three pillars of v3.0 UI:

1. [Usage of UI component framework introduced in 2.4.](../ui-component-framework/index.md)
2. [Bootstrap v3.4.1 to v5.x upgrade.](./upgrading-from-bootstrap-v3-to-v5.md)
3. [New Nautobot custom UI APIs.](./new-nautobot-custom-ui-apis.md)

!!! tip
    You are strongly encouraged to adopt the UI component framework. Migration can be performed incrementally on your 2.4 instance, making future upgrades easier. New features will be added exclusively to this framework. For example, the Data Compliance tab, automatic "copy" buttons in detail views, and collapsible cards or panels are already only available for models using the new UI component framework. The feature set will continue to expand over time.

Remember to follow our [UI Best Practices](../../../core/ui-best-practices.md) and to run the command `nautobot-migrate-bootstrap-v3-to-v5 <path> --resize`.

Some common use cases to have HTML embedded within Python include `views.py`, `template_content.py`, `templatetags.py` and `tables.py`.

## Template Migrations

!!! tip
    You can safely skip this section if you do not have any custom apps or can run `nautobot-migrate-deprecated-templates <path> --dry-run` against your custom app without any fixes suggested.

!!! tip
    You can adjust this in Nautobot 2.x prior to upgrading.

In Nautobot 3.0 we have migrated many no longer used templates. These templates all have direct replacements that can be changed with the single command `nautobot-migrate-deprecated-templates`.

## Removed Classes

!!! tip
    You can safely skip this section if you do not have any custom apps or can run `pylint --disable=all --enable=nb-deprecated-class --load-plugins=pylint_nautobot --rcfile=/dev/null <path>` against your custom app without any fixes suggested.

!!! tip
    You can adjust this in Nautobot 2.x prior to upgrading.

In Nautobot 3.0 we have migrated many no longer used classes. Every one of these classes has a direct replacement and is provided in the output to the replacement of it.

```bash
************* Module nautobot_example_app.custom_validators.py
nautobot_example_app/custom_validators.py.py:17:0: E4293: Class nautobot.extras.plugins.PluginCustomValidator is deprecated. Use nautobot.apps.models.CustomValidator instead. (nb-deprecated-class)
```

From:

```python
from nautobot.extras.plugins import PluginCustomValidator

class RelationshipAssociationCustomValidator(PluginCustomValidator):
```

To:

```python
from nautobot.apps.models import CustomValidator

class RelationshipAssociationCustomValidator(CustomValidator):
```

## Data Validation Engine

!!! tip
    You can safely skip this section if you do not reference `DataComplianceRule` or `ComplianceError` in your code.

The Data Compliance feature set from the Data Validation Engine App has been moved directly into core. Import paths that reference `nautobot_data_validation_engine.custom_validators.DataComplianceRule` or `nautobot_data_validation_engine.custom_validators.ComplianceError` should be updated to `nautobot.apps.models.DataComplianceRule` and `nautobot.apps.models.ComplianceError`, respectively.

## GraphQL

!!! tip
    You can safely skip this section if you do not reference `execute_query` or `execute_saved_query` in your code.

Code that calls the GraphQL `execute_query()` and `execute_saved_query()` functions may need to be updated to account for changes to the response object returned by these APIs. Specifically, the `response.to_dict()` method is no longer supported, but instead the returned data and any errors encountered may now be accessed directly as `response.data` and `response.errors` respectively.

## Minor Filtering Changes

!!! tip
    You can safely skip this section if `nautobot-server validate_models extras.dynamicgroup` runs without error.

A small number of breaking [filter field changes](../../../../release-notes/version-3.0.md#filter-standardization-improvements-1889) may impact Dynamic Group filter definitions; you are recommended to run `nautobot-server validate_models extras.dynamicgroup` (or the newly added `Validate Model Data` system Job) after the upgrade to identify any impacted Dynamic Groups. The models include:

- Front Port Templates `rear_port_template` filter
- Power Outlets `power_port` filter
- Module Bays `parent_module` filter
- Job Log Entries `job_result` filter
- Job Results `user` filter
- IP Address to Interface `ip_address` filter

There is no effect on REST API or GraphQL queries, as this is additive in those cases.

## Many-to-Many Fields in REST API

!!! tip
    You can safely skip this section if you do not use the REST API and only a minor modification needed if pynautobot user.

!!! tip
    You can adjust this in Nautobot 2.x.

In order to improve performance at scale, the REST API now defaults to excluding many-to-many fields (except for `tags`, `content_types`, and `object_types`) by default. Any code that relies on including many-to-many fields in the REST API response must explicitly request them by specifying the `exclude_m2m=False` query parameter. See [Filtering Included Fields](../../../../user-guide/platform-functionality/rest-api/filtering.md#filtering-included-fields) for more details.

Pynautobot users should ensure they add `exclude_m2m=False` to an individual request (`nb.dcim.devices.all(exclude_m2m=False)`) or (in pynautobot v3.0.0+) set the default for all requests (`import pynautobot; nb = pynautobot.api(url, token, exclude_m2m=False)`) to maintain prior behavior.

Nautobot Ansible users (using v6.0.0+ and pynautobot v3.0.0+) should see no change required when using module or inventory plugins. When using a lookup plugin, however, they will need to use the `api_filters` parameter to include M2M fields. For example: `api_filters='exclude_m2m=False'`.

In order to identify where an m2m field may be, let's review these two examples

```bash
curl -X 'GET' \
  'https://next.demo.nautobot.com/api/dcim/interfaces/19b12dc4-a475-500e-958f-b5dea028130f/?exclude_m2m=false' \
  -H 'accept: application/json' \
  -H "Authorization: Token $TOKEN"
```

```python
{
    "id": "19b12dc4-a475-500e-958f-b5dea028130f",
    "object_type": "dcim.interface",
    "display": "GigabitEthernet1",
    "url": "https://next.demo.nautobot.com/api/dcim/interfaces/19b12dc4-a475-500e-958f-b5dea028130f/",
    "device": {
        "id": "43e0c7a2-3939-5fcf-bc2f-c659f1c40d46",
        "object_type": "dcim.device",
        "url": "https://next.demo.nautobot.com/api/dcim/devices/43e0c7a2-3939-5fcf-bc2f-c659f1c40d46/",
    },
    "status": {
        "id": "bf03f613-7663-5ed6-bee3-f05d588065cc",
        "object_type": "extras.status",
        "url": "https://next.demo.nautobot.com/api/extras/statuses/bf03f613-7663-5ed6-bee3-f05d588065cc/",
    },
    "role": {
        "id": "77d3c3df-f983-51c2-aa1f-6ee7ebe646e2",
        "object_type": "extras.role",
        "url": "https://next.demo.nautobot.com/api/extras/roles/77d3c3df-f983-51c2-aa1f-6ee7ebe646e2/",
    },
    "untagged_vlan": null,
    "tagged_vlans": [              # <--------------- This only shows up in `exclude_m2m=False`
        {
            "id": "4eaf3921-1dd2-58b1-a86e-6cf01bb812f9",
            "object_type": "ipam.vlan",
            "url": "https://next.demo.nautobot.com/api/ipam/vlans/4eaf3921-1dd2-58b1-a86e-6cf01bb812f9/",
        },
        {
            "id": "c91906db-290e-50c8-89ef-5e60d71c1307",
            "object_type": "ipam.vlan",
            "url": "https://next.demo.nautobot.com/api/ipam/vlans/c91906db-290e-50c8-89ef-5e60d71c1307/",
        },
    ],
}
```

```bash
curl -X 'GET' \
  'https://next.demo.nautobot.com/api/dcim/interfaces/19b12dc4-a475-500e-958f-b5dea028130f/' \ # this is equivalant of `?exclude_m2m=true` in 3.0.
  -H 'accept: application/json' \
  -H "Authorization: Token $TOKEN"
```

```python
{
    "id": "19b12dc4-a475-500e-958f-b5dea028130f",
    "object_type": "dcim.interface",
    "display": "GigabitEthernet1",
    "url": "https://next.demo.nautobot.com/api/dcim/interfaces/19b12dc4-a475-500e-958f-b5dea028130f/",
    "device": {
        "id": "43e0c7a2-3939-5fcf-bc2f-c659f1c40d46",
        "object_type": "dcim.device",
        "url": "https://next.demo.nautobot.com/api/dcim/devices/43e0c7a2-3939-5fcf-bc2f-c659f1c40d46/",
    },
    "status": {
        "id": "bf03f613-7663-5ed6-bee3-f05d588065cc",
        "object_type": "extras.status",
        "url": "https://next.demo.nautobot.com/api/extras/statuses/bf03f613-7663-5ed6-bee3-f05d588065cc/",
    },
    "role": {
        "id": "77d3c3df-f983-51c2-aa1f-6ee7ebe646e2",
        "object_type": "extras.role",
        "url": "https://next.demo.nautobot.com/api/extras/roles/77d3c3df-f983-51c2-aa1f-6ee7ebe646e2/",
    },
    "untagged_vlan": null,
}
```

As you will note in the truncated output, that the many-to-many field does not show up in `exclude_m2m=False`. As noted, `tags`, `content_types`, and `object_types` will still show in either scenario as they are generally lower cardinality and on many models. A list of common many-to-many fields that you may use via the API include:

- CloudNetwork.prefixes
- CloudService.cloud_networks
- ControllerManagedDeviceGroup.radio_profiles
- ControllerManagedDeviceGroup.wireless_networks
- Device.clusters
- Device.software_image_files
- DeviceType.software_image_files
- DynamicGroup.children
- Interface.ip_addresses
- Interface.tagged_vlans
- InterfaceRedundancyGroup.interfaces
- InventoryItem.software_image_files
- ObjectPermission.groups
- ObjectPermission.users
- Prefix.locations
- RadioProfile.supported_data_rates
- SecretsGroup.secrets
- Team.contacts
- VLAN.ip_addresses
- VLAN.locations
- VMInterface.ip_addresses
- VMInterface.tagged_vlans
- VRF.devices
- VRF.export_targets
- VRF.import_targets
- VRF.prefixes
- VRF.virtual_device_contexts
- VRF.virtual_machines
- VirtualDeviceContext.interfaces
- VirtualMachine.software_image_files
