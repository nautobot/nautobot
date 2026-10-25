# Racks

The rack model represents a physical two- or four-post equipment rack in which devices can be installed. Each rack must be assigned to a location, and may optionally be assigned to a rack group and/or tenant. Racks can also be organized by user-defined functional roles.

Rack height is measured in _rack units_ (U); racks are commonly between 42U and 48U tall, but Nautobot allows you to define racks of arbitrary height. A toggle is provided to indicate whether rack units are in ascending (from the ground up) or descending order.

Each rack is assigned a name and (optionally) a separate facility ID. This is helpful when leasing space in a data center your organization does not own: The facility will often assign a seemingly arbitrary ID to a rack (for example, "M204.313") whereas internally you refer to is simply as "R113." A unique serial number and asset tag may also be associated with each rack.

A rack must be designated as one of the following types:

* 2-post frame
* 4-post frame
* 4-post cabinet
* Wall-mounted frame
* Wall-mounted cabinet

Similarly, each rack must be assigned an operational [`status`](../../platform-functionality/status.md). The following statuses are available by default:

* Reserved
* Available
* Planned
* Active
* Deprecated

Each rack has two faces (front and rear) on which devices can be mounted. Rail-to-rail width may be 10, 19, 21, or 23 inches. The outer width and depth of a rack or cabinet can also be annotated in millimeters or inches.

## Rack Power Utilization

The power utilization of a rack is calculated when one or more power feeds are assigned to the rack and connected to devices that draw power.

Here are the typical instances required for the power utilization of a rack to be calculated and shown in the web UI:

* **Power Panel** in the same location as the rack
* **Power Feed** assigned to the power panel and to the rack
* 1 **Device** (i.e. PDU)
    * power port connected to the power feed
    * power outlet(s) connected to the power port of itself
* 1 or more **Devices**
    * power port connected to a power outlet of the PDU

The total power utilization for a rack is calculated as the allocated apparent power draw, in volt-amperes (VA), divided by the total available power of all power feeds assigned to the rack. Allocated draw values are converted from watts to VA using the power factor of the power port reporting the draw.

For each power port directly connected to a power feed:

* If `allocated_draw` is set, the port's own allocated draw is used and downstream outlet loads are not added again.
* If `allocated_draw` is unset, the allocated draw of downstream power ports connected to that port's power outlets is used instead, even if `maximum_draw` is set on the upstream port.

!!! note
    To calculate rack utilization from downstream loads, leave `allocated_draw` unset on the PDU's upstream power port. An explicitly configured `allocated_draw` of zero takes precedence over downstream loads. Setting only `maximum_draw` does not override downstream allocated loads in the rack calculation.

### Per-Phase Power Utilization

For three-phase power feeds, the rack detail page can also display utilization for feed legs A, B, and C. Each three-phase feed contributes one third of its available power to each leg. Downstream allocated loads are assigned to a leg using the `feed_leg` of the PDU power outlet to which they are connected.

The per-phase graphs are shown only when three-phase capacity is available and all connected loads on those feeds can be attributed to a leg. If an upstream power port has `allocated_draw` set, or a connected downstream power port is supplied by an outlet without a `feed_leg`, the per-phase graphs are hidden and only the overall graph is shown. Unconnected outlets without a `feed_leg` do not prevent the graphs from being displayed.

!!! note
    The overall utilization includes all power feeds assigned to the rack, but the per-phase graphs include only three-phase feeds. On a rack with both single-phase and three-phase feeds, the sum of the per-phase loads and capacities therefore does not necessarily equal the overall load and capacity.

## Rack Height Configuration

+++ 2.4.22

When creating a new rack in the Nautobot web interface, the default rack height is pre-filled in the form. This default value can be customized via the `RACK_DEFAULT_U_HEIGHT` setting in the Nautobot UI configuration, accessible via **Admin → Configuration → Config** setting. This will be in the "Rack Elevation Rendering" section. The value must be a positive integer between 1 and 500 rack units. The default is 42 for 42U. This is an Integer only setting.

Note: This configuration only affects the initial value displayed in the rack creation form. Users can override this value when creating each individual rack. Existing racks and API-based rack creation are not affected by this setting.
