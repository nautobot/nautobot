# Controller Managed Device Groups

A Controller Managed Device Group in Nautobot models the relationship between [controllers](./controller.md) and the [devices](./device.md) they manage.

Each device can be assigned to only one Controller Managed Device Group through the `Device.controller_managed_device_group` field.

Similarly, each group is linked directly to a Controller via the `ControllerManagedDeviceGroup.controller` field. This link represents the control connection between the controller and the devices in the group.

Groups can be arranged in a hierarchical structure. The `ControllerManagedDeviceGroup.parent` field is used to depict this tree structure of the controlled devices. To organize child groups within a parent group, use the `ControllerManagedDeviceGroup.weight` field. All child groups must be assigned to the same controller as the parent group.

For more detailed information about model relations, please refer to the [developer documentation](../../../development/core/controllers.md).

## Examples

```yaml
controller_managed_device_group:
  - name: campus
    controller: Panorama1
    tags:
      - high_security
    devices:
      - dal-fw01
      - chi-fw01
  - name: dc
    controller: Panorama1
    tags:
      - medium_security
    devices:
      - nyc-fw99
      - jcy-fw99
```
