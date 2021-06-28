# Creating Devices in Nautobot

A network Device in Nautobot has a few required attributes:

* A Device Role
* A Device Type
    * A Device Type requires a Manufacturer
* A Site

Looking at the list above, there are four objects in Nautobot that must be present prior to creating a related Device.
The following sections will guide you through how to create each object type.

## Creating a Device Role

To create a new Device, you will need an existing Device Role or need to create a new Device Role instance.

To create a new Device Role:

1. Click on **Devices** in the top navigation menu
2. Find **Device Roles** on the drop-down menu
3. Select `+`
4. In the `Add a new device role` form, populate a Name
    * The Slug will auto-populate based on the Name, but can be manually overwritten
5. Click on Create    

![](../images/getting-started-nautobot-ui/3-create-role.png)

## Creating a Manufacturer

To create a new Device Type, you will need an existing Manufacturer or need to create a new Manufacturer instance.

To create a new Manufacturer:

1. Click on **Devices** in the top navigation menu
2. Find **Manufacturers** on the drop-down
3. Select `+`
4. In the `Add a new manufacturer` form, populate the Name
     * The Slug will auto-populate based on the Name, but can be manually overwritten
5. Click on **Create**

![](../images/getting-started-nautobot-ui/2-create-manufacturer.png)

## Creating a Device Type

To create a new Device, you will need an existing Device Type or need to create a new Device Type instance.

To create a new Device Type:

1. Click on **Devices** in the top navigation menu
2. Find **Device Types**
3. Select `+` to go to the `Add a new device type` form
4. Select the Manufacturer from the drop-down selector
5. Select the Model from the drop-down selector
6. Click on **Create**

![](../images/getting-started-nautobot-ui/4-create-device-type.png)

## Creating a Site

To create a new Device, you will need an existing Site or need to create a new Site instance.

To create a new Site:

1. Click on **Organization** in the top navigation menu
2. Find **Sites**
3. Select `+` to go to the `Add a new site` form
4. Populate the Site's Name
    * The Slug will auto-populate based on the Name, but can be manually overwritten
5. Set the Status to `Active` in the drop-down selector
6. Click on **Create** at the bottom of the form (not shown)

![](../images/getting-started-nautobot-ui/1-create-site.png)

## Creating a Device

To create a new Device:

1. Click on **Devices** in the top navigation menu
2. Find **Devices**
3. Select `+` to go to the `Add a new device` form

4. Populate the Name
5. Select the Device Role from the drop-down selector
6. Select the Device Type from the down-down selector
7. Select the Site from the drop-down selector
8. Set the Status to the appropriate value in the drop-down selector
9. Click on **Create** at the bottom of the form (not shown)

![](../images/getting-started-nautobot-ui/5-create-device.png)
