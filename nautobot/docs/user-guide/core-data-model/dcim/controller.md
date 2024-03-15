# Controllers

A Controller in Nautobot is an abstraction meant to represent network or SDN (Software-Defined Networking) controllers. These may include, but are not limited to, wireless controllers, cloud-based network management systems, and other forms of central network control mechanisms.

The Controller model is central to representing an entity that oversees one or more devices or device groups. It serves as the focal point for control and management operations within a network. A Controller can be associated with either individual devices or with groups of devices through a `DeviceRedundancyGroup`.

Key Features:

- **Versatile Modeling:** Suitable for a variety of controllers including Cisco ACI, Juniper MIST, Arista CloudVision, Meraki, and more.
- **Device Management:** Allows for the representation of relationships between controllers and the devices or device groups they manage.
- **Inventory Queries:** Simplifies finding devices or groups managed by a specific controller, enhancing visibility and management.

For more detailed information about controllers, please refer to the [developer documentation](../../../development/core/controllers.md).
