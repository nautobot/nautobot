# Software Image Files and Versions

The [Software Image File](../core-data-model/dcim/softwareimagefile.md) and [Software Version](../core-data-model/dcim/softwareversion.md) models are used to track the Software Versions of [Devices](../core-data-model/dcim/device.md), [Inventory Items](../core-data-model/dcim/inventoryitem.md) and [Virtual Machines](../core-data-model/virtualization/virtualmachine.md) and their associated image files.

## Create a Software Version

!!! note
    Before creating a Software Version, you must have an existing [Platform](../core-data-model/dcim/platform.md) to associate the Software Version to.

To create a new Software Version, navigate to **Devices > Software Versions** and click **Add**. (`/dcim/software-versions/add/`) The `Platform`, `Version` and `Status` fields are all required. You can use the `Alias` field if you would like to add a friendly name for the Software Version. There are optional fields for `Release Date`, `End of Support Date`, `Documentation URL` and booleans for `Long Term Support` and `Pre-Release`.

![Create a Software Version](images/software-image-files-and-versions/ss_software-version-create_light.png#only-light){ .on-glb }
![Create a Software Version](images/software-image-files-and-versions/ss_software-version-create_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/dcim/software-versions/add/`"

## Create a Software Image File

!!! note
    Before creating a Software Image File, you must have an existing Software Version to associate the Software Image File to.

To create a new Software Image File, navigate to **Devices > Software Image Files** and click **Add**. (`/dcim/software-image-files/add/`) The `Software Version`, `Image File Name` and `Status` fields are all required. There are optional fields for `Image File Checksum`, `Hashing Algorithm`, `Image File Size`, `Download URL`, `Default Image`, and `Device Types`.

![Create a Software Image File](images/software-image-files-and-versions/ss_software-image-file-create_light.png#only-light){ .on-glb }
![Create a Software Image File](images/software-image-files-and-versions/ss_software-image-file-create_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/dcim/software-image-files/add/`"

## Assigning Software Image Files to Device Types

Before a Device can be associated to a Software Version, the Software Version must contain either a Software Image File marked as the default image, or one or more Software Image Files associated to the Device's [Device Type](../core-data-model/dcim/devicetype.md). In the UI, Device Types can be associated to Software Image Files either on the Device Type form or the Software Image File form. Through the REST API, you must make these associations using the through model `dcim.DeviceTypeToSoftwareImageFile` at `/api/dcim/device-types-to-software-image-files/`.

## Assigning Software Versions to Devices, Inventory Items and Virtual Machines

Devices, Inventory Items and Virtual Machines may be associated to one Software Version to track their current version. This association can be made in the UI on the Device, Inventory Item or Virtual Machine forms. Through the REST API, the Software Version can be associated on the Device, Inventory Item and Virtual Machine REST API POST/PUT/PATCH views.

![Assign Software Version to Device](images/software-image-files-and-versions/ss_assign-software-version-to-device_light.png#only-light){ .on-glb }
![Assign Software Version to Device](images/software-image-files-and-versions/ss_assign-software-version-to-device_dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/dcim/devices/add/`"

### Assigning Software Image Files to Devices, Inventory Items and Virtual Machines

By default, the Software Image Files associated to a Software Version will be inherited by a Device, Inventory Item or Virtual Machine with the same Software Version. However, you can override this behavior by directly associating Software Image File to the Device, Inventory Item or Virtual Machine. This association can be made in the UI on the Device, Inventory Item or Virtual Machine forms. Through the REST API, the Software Image File can be associated on the Device, Inventory Item and Virtual Machine REST API POST/PUT/PATCH views.
