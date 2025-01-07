# Controllers

A Controller in Nautobot is an abstraction meant to represent network or SDN (Software-Defined Networking) controllers. These may include, but are not limited to, wireless controllers, cloud-based network management systems, and other forms of central network control mechanisms.

## Key Features

- **Flexible Modeling:** Fits various network management scenarios, including SDN controllers, wireless controllers, and cloud-based services.
- **Device Management:** Allows for the representation of relationships between controllers and the devices or device groups they manage.
- **Inventory Queries:** Simplifies finding devices or groups managed by a specific controller, enhancing visibility and management.

## Use Cases

These models support the representation of various use cases, including, but not limited to:

- Cisco ACI
- Panorama
- Juniper MIST
- Arista CloudVision
- Meraki
- Wireless Controllers (e.g., Ruckus, Cisco)
- OpenStack

**Using controllers enables answering inventory-related queries:**

Find the controller for the given device group:

```python
controller_managed_device_group_name = "DC-East-APIC"
controller = ControllerManagedDeviceGroup.objects.get(name=controller_managed_device_group_name).controller
```

Find the controller for the given device:

```python
device_name = "DC-East-APIC-1"
controller = Device.objects.get(name=device_name).controller_managed_device_group.controller
```

List device groups managed by the controller:

```python
controller_name = "Cisco ACI APIC - east"
device_groups = ControllerManagedDeviceGroup.objects.filter(controller__name=controller_name)
device_groups.count()
```

List devices managed by the controller:

```python
controller_name = "Cisco ACI APIC - east"
devices = Device.objects.filter(controller_managed_device_group__controller__name=controller_name)
devices.count()
```

## Base Fields

A controller is identified by a unique `name` and can include a `description` and optionally one or more `capabilities`.

### Capabilities

+++ 2.4.0

The capabilities field will be used to track the features that will be displayed on the Controller. As an example, the `wireless` choice will add the Controller to the Wireless Controllers link on the Navbar, and enable the Wireless tab on the Controller object.

## Related Models

A controller can be deployed to either an individual [Device](./device.md) or to a group of devices defined as a [Device Redundancy Group](./deviceredundancygroup.md) via `controller_device` or `controller_device_redundancy_group` fields. These fields are mutually exclusive.

Each controller can also be connected to a [Platform](./platform.md) and a specific [External Integration](../../platform-functionality/externalintegration.md) to define its connection to an external system.

A specific [Status](../../platform-functionality/status.md) and [Location](./location.md) are required for each controller.

For better organization and categorization, a [Role](../../platform-functionality/role.md), [Tenant](../tenancy/tenant.md) or [tags](../../platform-functionality/tag.md) can be assigned to the controller.

[Controller Managed Device Group](./controllermanageddevicegroup.md) represents the connection between the controller and devices it manages. It allows for the organization of controlled devices into hierarchical groups for structured representation.

For more detailed information about model relations, please refer to the [developer documentation](../../../development/core/controllers.md).

## Examples

### Cisco ACI

```yaml
name: Cisco ACI APIC - east
status: Active
controller_device: DC-East-APIC-1
location: DC-East
platform: cisco_apic
```

### Cisco Meraki

```yaml
name: Cisco Meraki SAAS
status: Active
controller_device: ~
location: Cloud Location
platform: cisco_meraki
```
