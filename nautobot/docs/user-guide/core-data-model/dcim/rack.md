# Racks

The rack model represents a physical two- or four-post equipment rack in which devices can be installed. Each rack must be assigned to a location, and may optionally be assigned to a rack group and/or tenant. Racks can also be organized by user-defined functional roles.

Rack height is measured in *rack units* (U); racks are commonly between 42U and 48U tall, but Nautobot allows you to define racks of arbitrary height. A toggle is provided to indicate whether rack units are in ascending (from the ground up) or descending order.

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

The total power utilization for a rack is calculated as the sum of all allocated draw (from power ports of devices either directly connected to a power feed or connected to a power outlet of a device that is connected to a power feed) divided by the Total Power (Amps × Volts × Max Utilization %) for all power feeds.
