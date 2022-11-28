<!-- markdownlint-disable MD024 -->

# Nautobot v2.0

This document describes all new features and changes in Nautobot 2.0.

If you are a user migrating from Nautobot v1.X, please refer to the ["Upgrading from Nautobot v1.X"](../installation/upgrading-from-nautobot-v1.md) documentation.

## Release Overview

### Added

### Changed

### Removed

#### Removed DCIM Shadowed Filter Fields ([#2421](https://github.com/nautobot/nautobot/pull/2804))

As a part of breaking changes made in v2.0, we removed shadowed filter fields exist in the DCIM app:

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

Now these two filter fields will be replaced by a single field using `NaturalKeyOrPKMultipleChoiceFilter`:

```python
    from nautobot.utilities.filters import NaturalKeyOrPKMultipleChoiceFilter
    site = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Site.objects.all(),
        label="Site (slug or ID)",
    )
```
Below is a table documenting all such changes and where they occurred.
[Insert Table]

There are also boolean membership filters using shadowed filter fields incorrectly in the DCIM App where a foreign-key related field is mapped to a boolean membership filter.

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
[Insert Table]

!!! important
    `NaturalKeyOrPKMultipleChoiceFilter` is not filtering on true Natural Keys in the case where its `to_field_name` argument is mapped to the `name` attribute or a single field that is not enough to identify an unique instance by itself. This is technically a bug and should be solved by resolving https://github.com/nautobot/nautobot/issues/2875.

<!-- towncrier release notes start -->
