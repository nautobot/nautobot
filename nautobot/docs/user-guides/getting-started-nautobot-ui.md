# Getting Nautobot Up and Running in the Web UI

## Introduction and Scope
The audience for this user guide is a user new to Nautobot. 
It is intended to assist the user with:
* Understanding the prerequisites to adding a new Device
* Creating the necessary prerequisite objects to add a new Device
* Adding new Devices
* Adding and understanding Regions
* Adding and Understanding Platforms
* Adding and Understanding Tenants and Tenant Groups
* Adding and Interfaces to a Device
* Adding VLANs and Understanding VLAN Groups
* Understanding IP Address Management (IPAM) in Nautobot


## Requirements
1. A functional Nautobot installation
2. Administrative rights in the Nautobot Web UI

## Creating Devices in Nautobot

A network Device in Nautobot has a few required attributes:
* A Device Role
* A Device Type
  * A Device Type requires a Manufacturer
* A Site

Looking at the list above, there are four objects in Nautobot that must be present prior to creating a related Device.
The following sections will guide you through how to create each object type.

### Creating a Device Role

You may use an appropriate existing Device Role or create a new one for a network Device.

To create a new Device Role:
1. Click on **Devices** in the top navigation menu
2. Find **Device Roles** on the drop-down menu
3. Select `+`
4. In the `Add a new device role` form, populate a Name
    * The Slug will auto-populate based on the Name you provide
5. Click on Create    

![](images/getting-started-nautobot-ui/3-create%20role.png)


### Creating a Manufacturer

You may use an appropriate existing Manufacturer or create a new instance for a Device Type.

To create a new Manufacturer:
1. Click on **Devices** in the top navigation menu
2. Find **Manufacturers** on the drop-down menu
3. Select `+`
4. In the `Add a new manufacturer` form, populate the Name
     * The Slug will auto-populate based on the Name you provide
5. Click on **Create**

![](images/getting-started-nautobot-ui/2-create%20manufacturer.png)

### Create a Device Type
You may use an appropriate existing Device Type or create a new instance for a Device.

To create a new Device Type:
1. Click on **Devices** in the top navigation menu



![](images/getting-started-nautobot-ui/4-create%20device%20type.png)




![](images/getting-started-nautobot-ui/1-create-site.png)







![](images/getting-started-nautobot-ui/5-create%20device.png)

