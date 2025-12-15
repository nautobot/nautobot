# IP Address Management

This next section will demonstrate how to:

* Create a Regional Internet Registry
* Create a Prefix
* Create assignable IP addresses
* Assign an IP address to an Interface on a Device

These type of operations fall under an umbrella called IP Address Management (IPAM).

## Creating a Regional Internet Registry (RIR)

A RIR allocates globally-routeable IP address space. There are five top-level RIRs, each responsible for a particular section of the globe.
Nautobot also considers RFCs 1918 and 6589 to be RIR-like because they allocate private IP space.

Nautobot requires any IP allocation be attributed to a RIR.

To create a RIR:

1. Click on **IPAM** in the left sidebar menu
2. Find **RIRs** and click on the **+**; this takes you to the `Add a new RIR` form
3. Specify the RIR `Name`
4. There is a checkbox to flag `Private` (internal use) only
5. Click on the `Create` button

![Add RIR](../images/getting-started-nautobot-ui/27-add-rir-light.png#only-light){ .on-glb }
![Add RIR](../images/getting-started-nautobot-ui/27-add-rir-dark.png#only-dark.png){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/ipam/rirs/add/`"

## Creating a Prefix

A Prefix is an IPv4 or IPv6 network and mask expressed in CIDR notation (e.g. 192.0.2.0/24).
Each Prefix can be assigned to a particular Location, an RIR and virtual routing and forwarding (VRF) instance.

To create a prefix:

1. Click on **IPAM** in the left sidebar menu
2. Look for **Prefixes** and click on the **+**
    * This will take you to the `Add a new prefix` form
3. Populate the `Prefix` in CIDR notation
4. If all addresses in the Prefix are usable, change the `Type` to "Pool"
5. Select a `Status` from the drop-down selector
6. Optionally select a `RIR` from the drop-down selector
7. Click on the `Create` button (not shown)

![Add prefix](../images/getting-started-nautobot-ui/30-add-prefix-light.png#only-light){ .on-glb }
![Add prefix](../images/getting-started-nautobot-ui/30-add-prefix-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/ipam/prefixes/add/`"

## Creating IP Addresses

To create an IP address:

1. Click on **IPAM** in the left side navigation menu
2. Find **IP Addresses** and click on the **+**
    * This will take you to the `Add a new IP address` form
3. In this example, we are going to create multiple individual addresses, so click on the `Bulk Create` tab
4. Populate an Address pattern
    * This example uses `10.10.10.[0-1,2-3,6-7]/31` to create 3 non-contiguous /31's
    * The specified mask should be exactly as would be configured on the Device's Interface
5. Select `Global` for `Namespace` from the drop-down selector
6. Select `Host` for `Type` from the drop-down selector
7. Select `Active` for `Status` from the drop-down selector
8. Click on the `Create` button

![Add IP address](../images/getting-started-nautobot-ui/32-add-ip-addr-light.png#only-light){ .on-glb }
![Add IP address](../images/getting-started-nautobot-ui/32-add-ip-addr-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/ipam/ip-addresses/bulk-add/`"

## Assigning IP Addresses

To assign an IP Address to a specific Device and Interface:

1. Click on **Devices** in the left side navigation menu
2. Click on **Devices** to go to the main page for Devices
3. Find the Device whose Interface you wish to associate to an IP Address and click on it, for example `ams01-asw-01`
4. Go to the `Interfaces` tab and look for the row with the Interface you are interested in, such as `TenGigabitEthernet1/1/1`
5. Click on the edit button for the Interface (a pencil icon)

![Assign IP address 1](../images/getting-started-nautobot-ui/33-assign-address-light.png#only-light){ .on-glb }
![Assign IP address 1](../images/getting-started-nautobot-ui/33-assign-address-dark.png#only-dark){ .on-glb }

![Assign IP address 2](../images/getting-started-nautobot-ui/34-assign-address-2-light.png#only-light){ .on-glb }
![Assign IP address 2](../images/getting-started-nautobot-ui/34-assign-address-2-dark.png#only-dark){ .on-glb }

Once on the `Editing Interface` page:

1. Select an `IP Address` from the drop-down selector, such as `10.0.0.1/32`
2. Click on the `Update` button
    * This will take you back to the Interfaces page for the Device, where you will see the assignment shown under the `IP Addresses` column

![Assign IP address 3](../images/getting-started-nautobot-ui/35-assign-address-3-light.png#only-light){ .on-glb }
![Assign IP address 3](../images/getting-started-nautobot-ui/35-assign-address-3-dark.png#only-dark){ .on-glb }

## Finding an IP Address for an Interface

1. Click on **Devices** in the left side navigation menu
2. Click on **Devices** to go to the main page for Devices
3. Search for the Device you are interested in (`ams01-asw-01` in this example) and click on the link to go to the main page for the Device
4. Go to the `Interfaces` tab and look for the row with the Interface you are interested in; find the IP Address(es) in the **IP Addresses** column in the row

![Verify IP address](../images/getting-started-nautobot-ui/36-verify-address-light.png#only-light){ .on-glb }
![Verify IP address](../images/getting-started-nautobot-ui/36-verify-address-dark.png#only-dark){ .on-glb }

## Finding IP Addresses in a Prefix

To find information on a particular Prefix:

1. Click on **IPAM** in the left side navigation menu
2. Click on **Prefixes** to get to the Prefixes main page
3. Find the Prefix you are interested in and click on the link, such as `10.10.10.0/24`
4. To view the available and allocated IP Addresses, click on the `IP Addresses` tab

![Verify prefix 1](../images/getting-started-nautobot-ui/37-verify-prefix-light.png#only-light){ .on-glb }
![Verify prefix 1](../images/getting-started-nautobot-ui/37-verify-prefix-dark.png#only-dark){ .on-glb }

![Verify prefix 2](../images/getting-started-nautobot-ui/38-verify-prefix2-light.png#only-light){ .on-glb }
![Verify prefix 2](../images/getting-started-nautobot-ui/38-verify-prefix2-dark.png#only-dark){ .on-glb }
