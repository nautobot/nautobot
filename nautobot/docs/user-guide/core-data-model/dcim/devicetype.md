# Device Types

A device type represents a particular make and model of hardware that exists in the real world. Device types define the physical attributes of a device (rack height and depth) and its individual components (console, power, network interfaces, and so on).

Device types are instantiated as devices installed within locations and/or equipment racks. For example, you might define a device type to represent a Juniper EX4300-48T network switch with 48 Ethernet interfaces. You can then create multiple _instances_ of this type named "switch1," "switch2," and so on. Each device will automatically inherit the components (such as interfaces) of its device type at the time of creation. However, changes made to a device type will **not** apply to instances of that device type retroactively.

Some devices house child devices which share physical resources, like space and power, but which functional independently from one another. A common example of this is blade server chassis. Each device type is designated as one of the following:

* A parent device (which has device bays)
* A child device (which must be installed within a device bay)
* Neither

!!! note
    This parent/child relationship is **not** suitable for modeling chassis-based devices, wherein child members share a common control plane. Instead, line cards and similarly non-autonomous hardware should be modeled as inventory items within a device, with any associated interfaces or other components assigned directly to the device.

## Device Component Templates

+++ 1.4.5
    The fields `created` and `last_updated` were added to all device component template models. If you upgraded from Nautobot 1.4.4 or earlier, the values for these fields will default to `None` (null).

Each device type is assigned a number of component templates which define the physical components within a device. These are:

* Console ports
* Console server ports
* Power ports
* Power outlets
* Network interfaces
* Front ports
* Rear ports
* Device bays (which house child devices)

Whenever a new device is created, its components are automatically created per the templates assigned to its device type. For example, a Juniper EX4300-48T device type might have the following component templates defined:

* One template for a console port ("Console")
* Two templates for power ports ("PSU0" and "PSU1")
* 48 templates for 1GE interfaces ("ge-0/0/0" through "ge-0/0/47")
* Four templates for 10GE interfaces ("xe-0/2/0" through "xe-0/2/3")

Once component templates have been created, every new device that you create as an instance of this type will automatically be assigned each of the components listed above. However, this automation occurs only when a device is first created: Adding or removing components on a device type does not automatically change existing device instances based on that device type.

!!! note
    Assignment of components from templates occurs only at the time of device creation. If you modify the templates of a device type, it will not affect devices which have already been created. This is intentional and by design as device type templates may evolve over time in your organization. However, you always have the option of adding, modifying, or deleting components on existing devices.

    Consider also that automatically changing components of existing devices when a device-type changes would require Nautobot to make very dangerous assumptions. For example, suppose you had a device type which included a specific line card with a specific set of interfaces. After creating some devices, representing your existing deployment of this device type, your deployment for new devices of this type changed to include a different line card and hence different interfaces, so you decided to update the device-type templates accordingly. If Nautobot were to automatically propagate this change to all existing devices of this type, it would result in an incorrect reflection of the reality that all existing devices have not yet been retrofitted with the new line card.
