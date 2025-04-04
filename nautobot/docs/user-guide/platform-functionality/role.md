# Roles

The Role model represents a role that can be assigned to a [device](../core-data-model/dcim/device.md), [rack](../core-data-model/dcim/rack.md), [virtual machine](../core-data-model/virtualization/virtualmachine.md), [IP address](../core-data-model/ipam/ipaddress.md), [VLAN](../core-data-model/ipam/vlan.md), or [prefix](../core-data-model/ipam/prefix.md). Each role is identified by a unique name and has a weight, color and content-types associated with it.

## Role Basics

The value of a `role` field on a model (such as `Device.role`) will be represented as a `nautobot.extras.models.Role` object.

When created, a `Role` can be associated to one or more model content-types using a many-to-many relationship. The relationship to each model is referenced across all user interfaces using the `{app_label}.{model}` naming convention (e.g. `dcim.device`).

Roles may be managed by navigating to **Organization > Roles** in the navigation menu.

Visit [role-internals](../../development/core/role-internals.md) to learn more about working with `role` as a developer.
