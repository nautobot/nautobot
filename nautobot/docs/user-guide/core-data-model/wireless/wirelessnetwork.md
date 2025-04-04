# Wireless Networks

Represents a WLAN network defined by SSID.

Fields on the Wireless Network include:

- Name
- SSID
- Description
- Mode
- Enabled
- Hidden
- [Secret](../../platform-functionality/secret.md)
- Authentication
- VLAN
- [Controller Managed Device Group](../dcim/controllermanageddevicegroup.md)

Future extensions could include captive_portal attribute, but are not scoped in the initial release. It should be implemented using [External Integrations](../../platform-functionality/externalintegration.md).

## Wireless Networks VLAN field

When adding a Controller Managed Device Group to a Wireless Network, there is the ability to add a VLAN. This VLAN is stored on the through table between Wireless Network and the Controller Managed Device Group. This allows the ability to use specific VLAN for each Wireless Network/Controller Managed Device Group relationship.
