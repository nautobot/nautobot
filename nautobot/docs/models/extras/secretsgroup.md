# Secrets Groups

+++ 1.2.0

A Secrets Group provides a way to collect and assign a purpose to one or more Secrets. The Secrets Group can then be attached to any object that needs to reference and make use of these Secrets, such as a Git repository needing a username/token to authenticate to a private GitHub repository, or a device using a group of Secrets to drive its NAPALM integration.

When creating or editing a Secrets Group, you can assign any number of defined Secrets to this group, assigning each secret an *access type* and a *secret type* that are unique within the context of this group. Some examples of how a Secrets Group might be populated for use by a given feature:

| Feature                   | Access Type | Secrets Type(s)                                     |
|---------------------------|-------------|-----------------------------------------------------|
| Git private repository    | `HTTP(S)`   | `Token`, possibly also `Username`                   |
| Device NAPALM integration | `Generic`   | `Username`, `Password`, possibly an enable `Secret` |

A Secrets Group is not limited to containing secrets of a single *access type* either - for example, a plugin that supports both NETCONF and gNMI protocols to interact with a device could be able to make use of a Secrets Group containing distinct secrets for each protocol.
