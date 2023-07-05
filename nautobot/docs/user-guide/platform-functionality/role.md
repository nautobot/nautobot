# Roles

The Role model represents a role that can be assigned to a device, rack, virtual machine, IP address, VLAN, or prefix. Each role is identified by a unique name and has a weight, color and content-types associated with it.

## Role Basics

The value of a `role` field on a model (such as `Device.role`) will be represented as a `nautobot.extras.models.Role` object.

When created, a `Role` can be associated to one or more model content-types using a many-to-many relationship. The relationship to each model is referenced across all user interfaces using the `{app_label}.{model}` naming convention (e.g. `dcim.device`).

Roles may be managed by navigating to **Organization > Roles** in the navigation menu.

### Importing Objects with a `role` Field

When using CSV import to reference a `role` field on an object, the `Role.name` field is used.

Visit [role-internals](../../development/core/role-internals.md) to learn more about working with `role` as a developer.
