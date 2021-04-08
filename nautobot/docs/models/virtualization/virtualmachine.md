# Virtual Machines

A virtual machine represents a virtual compute instance hosted within a cluster. Each VM must be assigned to exactly one cluster.

Like devices, each VM can be assigned a platform and/or functional role, and must have one of the following operational [`statuses`](https://nautobot.readthedocs.io/en/latest/models/extras/status/) assigned to it:

* Active
* Offline
* Planned
* Staged
* Failed
* Decommissioning

Status fields can now be customized via the new [`status`](https://nautobot.readthedocs.io/en/latest/models/extras/status/) model.

Additional fields are available for annotating the vCPU count, memory (GB), and disk (GB) allocated to each VM. Each VM may optionally be assigned to a tenant. Virtual machines may have virtual interfaces assigned to them, but do not support any physical component.
