<!-- markdownlint-disable MD024 -->

# Nautobot v2.2

This document describes all new features and changes in Nautobot 2.2.

## Release Overview

### Added

#### Contact and Team Models ([#230](https://github.com/nautobot/nautobot/issues/230))

Contact and Team are models that represent an individual and a group of individuals who can be linked to an object. Contacts and teams store the necessary information (name, phone number, email, and address) to uniquely identify and contact them. They are added to track ownerships of organizational entities and to manage resources more efficiently in Nautobot. Check out the documentation for [contact](../user-guide/core-data-model/extras/contact.md) and [team](../user-guide/core-data-model/extras/team.md). There is also a [user guide](../user-guide/feature-guides/contact-and-team.md) available on how to utilize these models.

#### Software Image and Software Version models ([#1](https://github.com/nautobot/nautobot/issues/1))

New models have been added for software images and software versions. These models are used to track the software versions of devices, inventory items and virtual machines and their associated image files. These models have been ported from the [Device Lifecycle Management App](https://github.com/nautobot/nautobot-app-device-lifecycle-mgmt/) and a future update to that app will migrate all existing data from the `nautobot_device_lifecycle_mgmt.SoftwareImageLCM` and `nautobot_device_lifecycle_mgmt.SoftwareLCM` models to the `dcim.SoftwareImage` and `dcim.SoftwareVersion` models added here.

Software versions must be associated to a platform. Software images must be associated to one software version and may be associated to one or more device types. Devices, inventory items and virtual machines may be associated to one software version to track their current version. See the documentation for [software image](../user-guide/core-data-model/dcim/softwareimage.md) and [software version](../user-guide/core-data-model/dcim/softwareversion.md). There is also a [user guide](../user-guide/feature-guides/software-images-and-versions.md) with instructions on how to create these models.

#### VLAN Location field enhancement ([#4412](https://github.com/nautobot/nautobot/issues/4412))

VLAN model has undergone modifications related to the `location` field. The primary change involves replacing the `location` field(ForeignKey), with a new `locations` field(ManyToManyField). To ensure backwards compatibility with pre-2.2 versions, the original location field has been retained as a `@property` field. Users can continue to interact with the location field in a manner consistent with previous versions.

#### Syntax highlighting ([#5098](https://github.com/nautobot/nautobot/issues/5098))

Language syntax highlighting for GraphQL, JSON, XML and YAML is now supported in the UI via JavaScript. To enable the feature, a code snippet has to be wrapped in the following HTML structure:

```html
<pre><code class="language-{graphql,json,xml,yaml}">...</code></pre>
```

[`render_json`](../user-guide/platform-functionality/template-filters.md#render_json) and [`render_yaml`](../user-guide/platform-functionality/template-filters.md#render_yaml) template filters default to this new behavior with an optional opt-out `syntax_highlight=False` arg.

#### Jobs tile view ([#5129](https://github.com/nautobot/nautobot/issues/5129))

Job list is now available in two display variants: list and tiles. List is a standard table view with no major changes introduced. Tiles is a new type of view displaying jobs in a two-dimensional grid.
