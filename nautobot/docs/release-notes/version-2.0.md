<!-- markdownlint-disable MD024 -->

# Nautobot v2.0

This document describes all new features and changes in Nautobot 2.0.

If you are a user migrating from Nautobot v1.X, please refer to the ["Upgrading from Nautobot v1.X"](../installation/upgrading-from-nautobot-v1.md) documentation.

## Release Overview

### Added

### Changed

### Removed

#### Removed DCIM Shadowed Filter Fields ([#2804](https://github.com/nautobot/nautobot/pull/2804))
 
As a part of breaking changes made in v2.0, shadowed filter/filterset fields are being removed in the dcim app:

Currently for foreign-key related fields, **on existing core models in the v1.3 release train**:
    - The field is shadowed for the purpose of replacing the PK filter with a lookup-based on a more human-readable value (typically `slug`, if available).
    - A PK-based filter is available as well, generally with a name suffixed by `_id`

For example:

```python
    site = django_filters.ModelMultipleChoiceFilter(
        field_name="site__slug",
        queryset=Site.objects.all(),
        to_field_name="slug",
        label="Site (slug)",
    )
    site_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Site.objects.all(),
        label="Site (ID)",
    )
```

Now these two fields will be replaced by a single field using `NaturalKeyOrPKMultipleChoiceFilter` introduced in v1.4:

```python
    from nautobot.utilities.filters import NaturalKeyOrPKMultipleChoiceFilter
    site = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Site.objects.all(),
        label="Site (slug or ID)",
    )
```
Below is a table documenting all such changes and where they occurred.

| Filterset                      | Old Filter Field   | Changes                                                                      |
|--------------------------------|--------------------|------------------------------------------------------------------------------|
| LocatableModelFilterSetMixin   | region_id          | Deleted                                                                      |
|                                | site_id            | Deleted                                                                      |
| RegionFilterSet                | parent_id          | Deleted                                                                      |
|                                | parent             | Changed to use `NaturalKeyOrPKMultipleChoiceFilter`                          |
| RackGroupFilterSet             | parent_id          | Deleted                                                                      |
|                                | parent             | Changed to use `NaturalKeyOrPKMultipleChoiceFilter`                          |
| RackFilterSet                  | group_id           | Deleted                                                                      |
|                                | role_id            | Deleted                                                                      |
|                                | role               | Changed to use `NaturalKeyOrPKMultipleChoiceFilter`                          |
|                                | serial             | Changed to use `MultiValueCharFilter`                                        |
| RackReservationFilterSet       | rack_id            | Deleted                                                                      |
|                                | group_id           | Deleted                                                                      |
|                                | user_id            | Deleted                                                                      |
|                                | user               | Changed to use `NaturalKeyOrPKMultipleChoiceFilter`                          |
| DeviceTypeFilterSet            | manufacturer_id    | Deleted                                                                      |
|                                | manufacturer       | Changed to use `NaturalKeyOrPKMultipleChoiceFilter`                          |
| PlatformFilterSet              | manufacturer_id    | Deleted                                                                      |
|                                | manufacturer       | Changed to use `NaturalKeyOrPKMultipleChoiceFilter`                          |
| DeviceFilterSet                | manufacturer_id    | Deleted                                                                      |
|                                | manufacturer       | Changed to use `NaturalKeyOrPKMultipleChoiceFilter`                          |
|                                | device_type_id     | Renamed to device_type Changed to use `NaturalKeyOrPKMultipleChoiceFilter`   |
|                                | role_id            | Deleted                                                                      |
|                                | role               | Changed to use `NaturalKeyOrPKMultipleChoiceFilter`                          |
|                                | platform_id        | Deleted                                                                      |
|                                | platform           | Changed to use `NaturalKeyOrPKMultipleChoiceFilter`                          |
|                                | rack_group_id      | changed to rack_group                                                        |
|                                | rack_id            | Renamed to rack Changed to use `NaturalKeyOrPKMultipleChoiceFilter`          |
|                                | cluster_id         | Renamed to cluster Changed to use `NaturalKeyOrPKMultipleChoiceFilter`       |
|                                | model              | Changed to use `NaturalKeyOrPKMultipleChoiceFilter`                          |
|                                | serial             | Changed to use `MultiValueCharFilter`                                        |
|                                | secrets_group_id   | Deleted                                                                      |
|                                | secrets_group      | Changed to use `NaturalKeyOrPKMultipleChoiceFilter`                          |
|                                | virtual_chassis_id | Renamed to virtual_chassis Changed to use `NaturalKeyOrPKMultipleChoiceFilter`|
| SiteFilterSet                  | region_id          | Deleted                                                                      |
| RackReservationFilterSet       | site_id            | Deleted                                                                      |
|                                | site               | Changed to use `NaturalKeyOrPKMultipleChoiceFilter`                          |
| DeviceComponentFilterSetMixin  | region_id          | Deleted                                                                      |
|                                | device_id          | Deleted                                                                      |
|                                | device             | Changed to use `NaturalKeyOrPKMultipleChoiceFilter`                          |
| CableTerminationFilterSetMixin | cabled             | Renamed to has_cable                                                         |
|                                | cable              | Changed to use `NaturalKeyOrPKMultipleChoiceFilter`                          |
| InterfaceFilterSet             | lag_id             | Deleted                                                                      |
| InventoryItemFilterSet         | region_id          | Deleted                                                                      |
|                                | site_id            | Deleted                                                                      |
|                                | site               | Changed to use `NaturalKeyOrPKMultipleChoiceFilter`                          |
|                                | device_id          | Deleted                                                                      |
|                                | device             | Changed to use `NaturalKeyOrPKMultipleChoiceFilter`                          |
|                                | parent_id          | Deleted                                                                      |
|                                | manufacturer_id    | Deleted                                                                      |
|                                | manufacturer       | Changed to use `NaturalKeyOrPKMultipleChoiceFilter`                          |
|                                | serial             | Changed to use `MultiValueCharFilter`                                        |
| VirtualChassisFilterSet        | region_id          | Deleted                                                                      |
|                                | site_id            | Deleted                                                                      |
|                                | site               | Changed to use `NaturalKeyOrPKMultipleChoiceFilter`                          |
|                                | master_id          | Deleted                                                                      |
|                                | master             | Changed to use `NaturalKeyOrPKMultipleChoiceFilter`                          |
|                                | tenant_id          | Deleted                                                                      |
|                                | tenant             | Changed to use `NaturalKeyOrPKMultipleChoiceFilter`                          |
| PowerPanelFilterSet            | rack_group_id      | Deleted                                                                      |
| PowerFeedFilterSet             | region_id          | Deleted                                                                      |
|                                | site_id            | Deleted                                                                      |
|                                | site               | Changed to use `NaturalKeyOrPKMultipleChoiceFilter`                          |
|                                | power_panel_id     | Deleted                                                                      |
|                                | rack_id            | Deleted                                                                      |

There are also instances where a foreign-key related field is incorrectly mapped to a boolean membership filter.

For example:

```python
    has_power_outlets = RelatedMembershipBooleanFilter(
            field_name="poweroutlets",
            label="Has power outlets",
        )
    power_outlets = has_power_outlets
```

Now we change the foregin-key related field to be its own PK based filter:

```python
    has_power_outlets = RelatedMembershipBooleanFilter(
            field_name="poweroutlets",
            label="Has power outlets",
        )
    power_outlets = django_filters.ModelMultipleChoiceFilter(
        queryset=PowerOutlet.objects.all(),
        field_name="poweroutlets",
        label="Power Outlets",
    )
```
Below is a table documenting all such changes and where they occurred.

| Filterset       | Old Filter Field     | Changes                                                                           |
|-----------------|----------------------|-----------------------------------------------------------------------------------|
| DeviceFilterSet | console_ports        | Changed from mapping to `has_console_ports` to `ModelMultipleChoiceFilter`        |
|                 | console_server_ports | Changed from mapping to `has_console_server_ports` to `ModelMultipleChoiceFilter` |
|                 | power_ports          | Changed from mapping to `has_power_ports` to `ModelMultipleChoiceFilter`          |
|                 | power_outlets        | Changed from mapping to `has_power_outlets` to `ModelMultipleChoiceFilter`        |
|                 | interfaces           | Changed from mapping to `has_interfaces` to `ModelMultipleChoiceFilter`           |
|                 | front_ports          | Changed from mapping to `has_front_ports` to `ModelMultipleChoiceFilter`          |
|                 | rear_ports           | Changed from mapping to `has_rear_ports` to `ModelMultipleChoiceFilter`           |
|                 | device_bays          | Changed from mapping to `has_device_bays` to `ModelMultipleChoiceFilter`          |
|                 | pass_through_ports   | deleted in exchange for in exchange for `has_(front|rear)_ports`                  |

!!! important
    `NaturalKeyOrPKMultipleChoiceFilter` is not filtering on true Natural Keys in the case where its `to_field_name` argument is mapped to the `name` attribute or a single field that is not enough to identify an unique model instance by itself. This is technically a bug and is tracked here https://github.com/nautobot/nautobot/issues/2875 and should be resolved after concluding this Epic https://github.com/nautobot/nautobot/issues/1574.

<!-- towncrier release notes start -->
