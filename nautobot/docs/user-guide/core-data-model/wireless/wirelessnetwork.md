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
- [Access Point Groups](accesspointgroup.md)

Future extensions could include captive_portal attribute, but are not scoped in the initial release. It should be implemented using Nautobot’s external integrations.

## Wireless Networks VLAN field

When adding an Access Point Group to a Wireless Network, there is the ability to add a VLAN. This VLAN is stored on the through table between Wireless Network and the Access Point Group. This allows the ability to use specific VLAN for each Wireless Network/Access Point Group relationship.
