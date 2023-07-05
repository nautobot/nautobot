# Circuits

A communications circuit represents a single _physical_ link connecting exactly two endpoints, commonly referred to as its A and Z terminations. A circuit in Nautobot may have zero, one, or two terminations defined. It is common to have only one termination defined when you don't necessarily care about the details of the provider side of the circuit, e.g. for Internet access circuits. Both terminations would likely be modeled for circuits which connect one customer location to another.

Each circuit is associated with a provider and a user-defined type. For example, you might have Internet access circuits delivered to each location by one provider, and private MPLS circuits delivered by another. Each circuit must be assigned a circuit ID, each of which must be unique per provider.

Each circuit must be assigned to a [`status`](../../platform-functionality/status.md). The following statuses are available by default:

* Planned
* Provisioning
* Active
* Offline
* Deprovisioning
* Decommissioned

Circuits also have optional fields for annotating their installation date and commit rate, and may be assigned to Nautobot tenants.

!!! note
    Nautobot currently models only physical circuits: those which have exactly two endpoints. It is common to layer virtualized constructs (_virtual circuits_) such as MPLS or EVPN tunnels on top of these, however Nautobot does not yet support virtual circuit modeling.
