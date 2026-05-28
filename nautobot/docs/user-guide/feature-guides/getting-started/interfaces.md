# Interfaces

Interfaces in Nautobot represent network interfaces used to exchange data with connected devices.

More information on Interfaces is in the [Interfaces](../../core-data-model/dcim/interface.md) section of the Nautobot documentation.

Interfaces can be added at the Device or the Device Type level:

* Interfaces added to an individual Device are for that Device only
* Interfaces added to the Device Type will be applied to all NEW implementations of that Device Type (not existing implementations)

Which one you select depends on your use case; in some instances you will need to use both, as in the example below.

## Interface Add Example

Let’s take an example, with the following goal:

* We want to define a Device Type of `MX240-edge`
* This Device Type will have 20x 10G (`xe-[0-1]/0/[0-9]`) Interfaces and one LAG (`ae0`) Interface
* The `xe-0/0/9` and `xe-1/0/9` Interfaces will be members of the `ae0` Interface

### Creating a Device Type

We are going to use the **Device Type** to achieve part of this goal. Using the **Device Type** will also provide repeatability
because the **Device Type** object also serves as a template. This templating feature is demonstrated in this example.

Device Types can serve as templates for Devices, and as such the two are very similar. Here is a screenshot of a Device Type:

![Device type example](../images/getting-started-nautobot-ui/21-device-type-light.png#only-light){ .on-glb }
![Device type example](../images/getting-started-nautobot-ui/21-device-type-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/dcim/device-types/add/`"

Creating a Device Type is very similar to [creating a Device](creating-devices.md).

To create a Device Type:

1. Click on **Devices** in the left sidebar menu
2. Under the **DEVICE TYPES** section, select **Device Types**
    * From this page you can view any existing Device Types
3. Click on the `Add device type` button to add new Device Type
    * A Device Type requires a **Manufacturer** object to be created prior to creating the Device Type
    * Device Type requires **Manufacturer**, **Model**, and **Height** values at creation
    * In this example, select `APC` from the **Manufacturer** drop-down selector, name the Device Type **Model** `APDU9941`, and input 5 for the **Height**
4. Click on `Create`
5. On the home page for the recently created Device Type, click on `+Add Components` and select `Interfaces`

![Create a device type](../images/getting-started-nautobot-ui/15-create-device-type-light.png#only-light){ .on-glb }
![Create a device type](../images/getting-started-nautobot-ui/15-create-device-type-dark.png#only-dark){ .on-glb }

You will now see the `Interface Template` form:

1. Add the `ae0` Interface Template
    * `Device Type` will auto-populate to the Device Type you are editing
    * Populate a `Name` of `ae0`
    * Select a `Type` of `Link Aggregation Group (LAG)` from the drop-down selector
    * Add a `Description` and `Label` (optional)
2. Click `Create and Add More`
3. Create the `xe-` Interfaces Template
    * Keep the same `Manufacturer` and `Device Type` as the previous step
    * Populate a `Name` of `xe-[0-1]/0/[0-9]`. Using the syntax of `[<start>-<end>]` for numbers in the name field like this will cause a bulk creation using the range of numbers provided.
    * Select the appropriate Type from the drop-down selector
4. Click on `Create`

![Create interface templates](../images/getting-started-nautobot-ui/16-interface-templates-light.png#only-light){ .on-glb }
![Create interface templates](../images/getting-started-nautobot-ui/16-interface-templates-dark.png#only-dark){ .on-glb }

Clicking the `Create` button will take you back to the home screen for the Device Type you are editing. There, you will
see that the **Interfaces** tab now has the expected 21 Interfaces listed.

![Example interface template](../images/getting-started-nautobot-ui/17-templated-interfaces-light.png#only-light){ .on-glb }
![Example interface template](../images/getting-started-nautobot-ui/17-templated-interfaces-dark.png#only-dark){ .on-glb }

!!! note
    Interfaces cannot be assigned in to a LAG in the Device Type template; component
    Interfaces must be designated in the specific instantiation of a Device created from the Device Type.

### Creating a New Device Using the Device Type

Create a new Device with these attributes:

* **Name** = `ang01-edge-01`
* **Role** select `edge`
* **Device type** select `APC APDU9941` (this will show up as a fusion of the **Manufacturer** (`APC`) for the Device Type and the Device Type (`APDU9941`) Names)
* **Location** select `ANGO1`
* **Status** select `Active`

On the main screen for the new *Device*, you will see an **Interfaces** tab with the expected Interfaces from the *Device Type* template:

![Assign device type](../images/getting-started-nautobot-ui/18-assign-device-type-light.png#only-light){ .on-glb }
![Assign device type](../images/getting-started-nautobot-ui/18-assign-device-type-dark.png#only-dark){ .on-glb }

!!! note
    Device Type properties only apply to **new** instantiations of Devices from the Type;
    Devices created prior to a modification of the Device Type will not inherit the changes retroactively

### Specifying the LAG Components on the Device

LAG component Interfaces cannot be assigned in the Device Type template, so we will
edit this new Device, specifying the component `ae0` Interfaces.

1. On the new Device's main page, select the appropriate Interfaces (`xe-0/0/9` and `xe-1/0/9`) to be added to `ae0` and click on the `Edit` button
2. On the `Editing Interfaces` form, select `ae0` in the `Lag` drop-down selector
3. Click on `Apply`; you will be taken back to the main page for the Device

![Edit LAG interface](../images/getting-started-nautobot-ui/19-edit-ints-for-lag-light.png#only-light){ .on-glb }
![Edit LAG interface](../images/getting-started-nautobot-ui/19-edit-ints-for-lag-dark.png#only-dark){ .on-glb }

On the Device's main page, notice that `xe-0/0/9` and `xe-1/0/9` are now assigned to the `ae0` LAG:

![LAG interface example](../images/getting-started-nautobot-ui/20-ints-int-lag-light.png#only-light){ .on-glb }
![LAG interface example](../images/getting-started-nautobot-ui/20-ints-int-lag-dark.png#only-dark){ .on-glb }
