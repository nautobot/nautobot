# Power Tracking

{%
    include-markdown "../models/dcim/powerpanel.md"
    heading-offset=1
%}
{%
    include-markdown "../models/dcim/powerfeed.md"
    heading-offset=1
%}

## Rack Power Utilization

The power utilization of a rack is calculated when one or more power feeds are assigned to the rack and connected to devices that draw power.

Here are the typical instances required for the power utilization of a rack to be calculated and shown in the web UI:

- **Power Panel** in the same site as the rack
- **Power Feed** assigned to the power panel and to the rack
- 1 **Device** (i.e. PDU)
    - power port connected to the power feed
    - power outlet(s) connected to the power port of itself
- 1 or more **Devices**
    - power port connected to a power outlet of the PDU

The total power utilization for a rack is calculated as the sum of all allocated draw (from power ports of devices either directly connected to a power feed or connected to a power outlet of a device that is connected to a power feed) divided by the Total Power (Amps × Volts × Max Utilization %) for all power feeds.

## Example Power Topology

![Power distribution model](../media/power_distribution.png)
