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
