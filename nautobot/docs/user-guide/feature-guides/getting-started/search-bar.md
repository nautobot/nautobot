# The Search Bar

The exercises in the prior sections in this *Getting Started Guide* walked you through how to **navigate** to the proper objects.

You can also use the Search Bar to find desired objects with either partial or complete alpha/numeric characters or exact UUID.

## Searching For an IP Address

1. Type in `10.10.10.0` in the Search Bar and click on `Search`
    * This takes you to a search results page
2. **Prefix** search result `10.10.10.0/24`
3. **IP Address** search result `10.10.10.0/31`

Clicking on any of these objects takes you to the main page for that object.
This example shows the result of clicking on the **IP Address** object (4).

![Address search v2](../images/getting-started-nautobot-ui/42-address-search-v2.png)

## Searching for a Device

1. Search for `edge`
    * This takes you to a search results page
2. In the drop-down selector to the right, select `Devices`
3. Search results for Devices with `edge` in the name
4. *Tenants* for each Device (if applicable)
5. *Device Type* for each Device
6. *Location* for each Device

Clicking on any of the links for the results takes you to the main page for that object. For example:

* Clicking on the `ANG01` Location takes you to the main page for the Location.
* Clicking on the `ang01-edge-02` Device takes you to the main page for the Device

![Device search results](../images/getting-started-nautobot-ui/41-device-search-results.png)
