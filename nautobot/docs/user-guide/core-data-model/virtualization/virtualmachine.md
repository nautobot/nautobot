# Virtual Machines

A virtual machine represents a virtual compute instance hosted within a cluster. Each VM must be assigned to exactly one cluster.

Like devices, each VM can be assigned a platform and/or functional role, and an operational [`status`](../../platform-functionality/status.md). The following statuses are available by default:

* Active
* Offline
* Planned
* Staged
* Failed
* Decommissioning

Additional fields are available for annotating the vCPU count, memory (GB), and disk (GB) allocated to each VM. Each VM may optionally be assigned to a tenant. Virtual machines may have virtual interfaces assigned to them, but do not support any physical component.

+/- 2.0.0
    In Nautobot 1.x, it was not possible to delete an IPAddress or an VMInterface that was serving as the primary IP address (`primary_ip4`/`primary_ip6`) for a VirtualMachine. As of Nautobot 2.0, this is now permitted; doing so will clear out the VirtualMachine's corresponding primary IP value.

+++ 3.3.0
    If the [`PRIMARY_IP_REQUIRES_INTERFACE_ASSIGNMENT`](../../administration/configuration/settings.md#primary_ip_requires_interface_assignment) setting is disabled, an IP address that isn't assigned to any interface can also be designated as a virtual machine's primary IP, including when creating the virtual machine. Such a primary IP is retained if it is later assigned to and then removed from the virtual machine's interfaces. An IP address assigned to another virtual machine's interface -- but _not_ to any interface on this virtual machine -- still can't be used as this virtual machine's primary IP.

+++ 2.2.0
    The [Software Version](../dcim/softwareversion.md) model has been introduced to represent the software version that is currently installed on a virtual machine. An optional software version field has been added to virtual machines.
