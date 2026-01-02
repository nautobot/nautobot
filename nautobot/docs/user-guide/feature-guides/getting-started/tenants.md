# Tenants

A 'Tenant' signifies ownership of an object in Nautobot and as such, any object may only have a single Tenant assigned.

More information on Tenants can be found in the [Tenants](../../core-data-model/tenancy/tenant.md) section of the Nautobot docs.

## Creating a Tenant

To create a Tenant:

1. Click on **Organization** on the left sidebar menu
2. Under **Tenancy** section, select **Tenants**
    * From this page you can view any existing Tenants
    * Click the `+ Add Tenant` button.
3. Populate the `Name` field
4. Click the `Create` button

![Add tenant](../images/getting-started-nautobot-ui/12-add-tenant-light.png#only-light){ .on-glb }
![Add tenant](../images/getting-started-nautobot-ui/12-add-tenant-dark.png#only-dark){ .on-glb }

## Assigning a Tenant to an Object

To add a Tenant to an existing Device:

1. Click on **Devices** in the left sidebar menu
2. Look for the **Devices** option and click on it
    * This will take you to the **Devices** page
3. Click on the specific Device you want to add the Tenant to
    * This will take you to the main page for that Device
4. On the specific Device page, click on the `Edit` button

![Assign tenant to device 1](../images/getting-started-nautobot-ui/13-assign-tenant-to-device-light.png#only-light){ .on-glb }
![Assign tenant to device 1](../images/getting-started-nautobot-ui/13-assign-tenant-to-device-dark.png#only-dark){ .on-glb }

Once on the page to edit the Device:

1. Make a selection from the `Tenant` drop-down menu selector
2. Click the `Update` button

This will take you back to the main page for the Device.

![Assign tenant to device 2](../images/getting-started-nautobot-ui/14-assign-tenant-to-device-2-light.png#only-light){ .on-glb }
![Assign tenant to device 2](../images/getting-started-nautobot-ui/14-assign-tenant-to-device-2-dark.png#only-dark){ .on-glb }

Notice that the `Tenant` field is now populated/updated.
