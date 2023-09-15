# Platforms

A platform defines the type of software running on a device or virtual machine. This can be helpful to model when it is necessary to distinguish between different versions or feature sets. Note that two devices of the same type may be assigned different platforms: For example, one Juniper MX240 might run Junos 14 while another runs Junos 15.

Platforms may optionally be limited by manufacturer: If a platform is assigned to a particular manufacturer, it can only be assigned to devices with a type belonging to that manufacturer.

The platform model can be used to indicate which "network driver" Nautobot (and Jobs, Apps, etc.) should use when connecting to a remote device running this platform. This is a generic string corresponding loosely to a [Netmiko](https://github.com/ktbyers/netmiko) driver name. As there are many different libraries and applications for connecting to a device, rather than having a separate model field for each such connection type, Nautobot uses [netutils](https://netutils.readthedocs.io/en/latest/) to translate the generic network driver string into a variety of library-specific driver strings (Ansible "collection name", PyATS "OS" value, Scrapli "platform", etc.) which can be accessed via the UI, REST API, and GraphQL as needed. An administrator can extend or override the default translations provided by netutils by configuring the [`NETWORK_DRIVERS`](../../administration/configuration/optional-settings.md#network_drivers) dictionary appropriately. (If your extensions are generally applicable, please consider making a pull request against [netutils](https://github.com/networktocode/netutils) to update the package!)

+++ 1.6.0
    The `network_driver` database field and the `network_driver_mappings` derived property were added to the Platform data model. Support for the `NETWORK_DRIVERS` setting was added.

For historical reasons, the [NAPALM](https://github.com/napalm-automation/napalm/) driver (`napalm_driver` field) and any associated arguments (`napalm_args` field) Nautobot should use when connecting to a remote device via NAPALM can (and must) be configured directly rather than being derived from the network driver. The name of the NAPALM driver along with optional parameters are stored with the platform.

Apps and Jobs should transition to using the `network_driver_mappings["napalm"]` property when connecting to a device via NAPALM. Nautobot may deprecate the use of the `napalm_driver` and `napalm_args` fields in a future release.

The assignment of platforms to devices is an optional feature, and may be disregarded if not desired.
