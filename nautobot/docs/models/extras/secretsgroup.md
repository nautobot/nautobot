# Secrets Groups

A secrets group provides a way to collect and assign a purpose to one or more [secrets](./secret.md). The secrets group can then be attached to any object that needs to reference and make use of these secrets, such as a [Git repository](./gitrepository.md) needing a username/token to authenticate to a private GitHub repository, or a [device](../dcim/device.md) using a group of secrets to drive its [NAPALM](../../additional-features/napalm.md) integration.

When creating or editing a secret group, you can assign any number of defined secrets to this group, assigning each secret an *access type* and a *secret type* that are unique within the context of this group. Some examples of how a secrets group might be populated for use by a given feature:

| Feature                   | Access Type | Secrets Type(s)                                     |
|---------------------------|-------------|-----------------------------------------------------|
| Git private repository    | `HTTP(S)`   | `Token`, possibly also `Username`                   |
| Device NAPALM integration | `Generic`   | `Username`, `Password`, possibly an enable `Secret` |

A secrets group is not limited to containing secrets of a single *access type* either - for example, a plugin that supports both NETCONF and gNMI protocols to interact with a device could be able to make use of a secrets group containing distinct secrets for each protocol.
