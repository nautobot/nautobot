# The Search Bar

The next couple sections walk you through finding different objects and verifying information about the objects. 
The instructions in those sections will walk you through how to **navigate** to the main page for the proper object. 

You can also use the search bar to find the desired object's page.

We will show two quick examples.

Example one:

1. Type in `10.10.10.0` in the Search Bar and click on `Search`
    * This takes you to a search results page
2. **Aggregate** search result `10.0.0.0/8` (this is the Aggregate for the Prefix `10.10.10.0/24`)
3. **Prefix** search result `10.10.10.0/24`
4. **IP Address** search result `10.10.10.0/31`
5. Interface related to `10.10.10.0/31` 
6. Interface Parent (Device) for `10.10.10.0/31`

Clicking on any of these objects takes you to the main page for that object.
This example shows the result of clicking on the **IP Address** object (4).

![](../images/getting-started-nautobot-ui/42-address-search-v2.png)

Example two shows a Device-specific search:

1. Search for `edge`
    * This takes you to a search results page
2. In the drop-down selector to the right, select **Devices**
3. Search results for Devices with `edge` in the name
4. *Tenants* for each Device (if applicable) 
5. *Device Type* for each Device
6. *Site* for each Device

Clicking on an of the links for the results takes you to the main page for that object. For example:

* Clicking on the `Vancouver 1` Site takes you to the main page for the Site.
* Clicking on the `edge2.van1` Device takes you to the main page for the Device

![](../images/getting-started-nautobot-ui/41-device%20search%20results.png)





