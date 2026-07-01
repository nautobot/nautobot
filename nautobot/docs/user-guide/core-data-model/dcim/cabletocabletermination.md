# Cable to Cable Termination

+++ 3.2

A "Cable to Cable Termination" is a record linking a specific connector of a given [cable](cable.md) to a terminating object (such as an [interface](interface.md), [front port](frontport.md), [circuit termination](../circuits/circuittermination.md), etc.)

A standard, connected, point-to-point cable would have two cable to cable termination records, one for the "A" side and one for the "B" side. If the cable is connected at only one end, it would only have one such record, and a fully disconnected cable in isolation would have none. Conversely, a breakout cable could have zero, one, two, or many such records, depending on its [cable type](cabletype.md) and how it's connected.

## Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `cable` | [cable](cable.md) | Yes | The cable this record is terminating |
| `cable_end` | string | Yes | "A" or "B" |
| `connector` | integer | Yes | The connector number on this end of the cable that this record is terminating (1 for a point-to-point cable) |
| `circuit_termination` | [circuit termination](../circuits/circuittermination.md) | No | |
| `console_port` | [console port](consoleport.md) | No | |
| `console_server_port` | [console server port](consoleserverport.md) | No | |
| `front_port` | [front port](frontport.md) | No | |
| `interface` | [interface](interface.md) | No | |
| `power_feed` | [power feed](powerfeed.md) | No | |
| `power_outlet` | [power outlet](poweroutlet.md) | No | |
| `power_port` | [power port](powerport.md) | No | |
| `rear_port` | [rear port](rearport.md) | No | |

### Validation

* The fields `cable`, `cable_end`, and `connector` must form a unique set (in other words, only one termination per physical connector per cable).
* Exactly one of the termination foreign keys (`circuit_termination`, `console_port`, etc.) must be set - the `termination` property (see below) must identify exactly one termination object that terminates this cable connector.
* The `connector` must be a valid in-range value for the given `cable_end` of its `cable`'s [cable type](cabletype.md), or must be exactly 1 for an untyped point-to-point cable.
* A cable cannot be terminated to virtual or wireless interfaces.
* A cable cannot be terminated to a circuit termination of a [provider network](../circuits/providernetwork.md).
* Multiple cables or connectors cannot be terminated to the same object.
* Breakout cables can only be terminated to interfaces, front ports, rear ports, and circuit terminations - not power or console terminations.
* Various logical pairings of termination types are enforced. For example it is not permitted to terminate the same cable both to an interface via one connector and to a power outlet via a different connector.

## Properties

| Property | Type | Description |
|----------|------|-------------|
| `termination` | record | The termination object (interface, circuit termination, etc.) to which this object terminates the cable |
| `termination_type` | content type | The type of the `termination` record |
| `termination_id` | UUID | The primary key of the `termination` record |

## REST API

Cable to cable termination records are exposed at `/api/dcim/cables-to-cable-terminations/`. Each record corresponds to a single connector/termination row as described above.

While individual records can be created, updated, and deleted through this endpoint, most consumers will find it more convenient to manage a cable's terminations as a set through the `terminations` field of the [cable](cable.md) REST API. This endpoint is primarily useful for querying the per-connector rows of a cable directly (for example via `/api/dcim/cables-to-cable-terminations/?cable=<cable-uuid>`), including for CSV export, since the cable endpoint's nested `terminations` field cannot be flattened into CSV. See the [Breakout Cables feature guide](../../feature-guides/breakout-cables.md) for more on the cable `terminations` field.
