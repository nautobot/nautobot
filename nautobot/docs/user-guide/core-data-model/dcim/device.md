# Devices

Every piece of hardware which is installed within a location or rack exists in Nautobot as a device. Devices are measured in rack units (U) and can be half depth or full depth. A device may have a height of 0U: These devices do not consume vertical rack space and cannot be assigned to a particular rack unit. A common example of a 0U device is a vertically-mounted PDU.

When assigning a multi-U device to a rack, it is considered to be mounted in the lowest-numbered rack unit which it occupies. For example, a 3U device which occupies U8 through U10 is said to be mounted in U8. This logic applies to racks with both ascending and descending unit numbering.

A device is said to be full-depth if its installation on one rack face prevents the installation of any other device on the opposite face within the same rack unit(s). This could be either because the device is physically too deep to allow a device behind it, or because the installation of an opposing device would impede airflow.

Each device must be instantiated from a pre-created device type, and its default components ([console ports](consoleport.md), [power ports](powerport.md), [interfaces](interface.md), etc.) will be created automatically. (The device type associated with a device may be changed after its creation, however its components will not be updated retroactively.)

Each device must be assigned a [location](location.md), device [role](../../platform-functionality/role.md), and operational [`status`](../../platform-functionality/status.md), and may optionally be assigned to a rack within a location. A platform, serial number, and asset tag may optionally be assigned to each device.

Device names must be unique within a location, unless the device has been assigned to a tenant. Devices may also be unnamed.

When a device has one or more interfaces with IP addresses assigned, a primary IP for the device can be designated, for both IPv4 and IPv6.

+/- 2.0.0
    In Nautobot 1.x, it was not possible to delete an IPAddress or an Interface that was serving as the primary IP address (`primary_ip4`/`primary_ip6`) for a Device. As of Nautobot 2.0, this is now permitted; doing so will clear out the Device's corresponding primary IP value.

For Devices forming a group (Failover, Load-Sharing, Redundacy or similar) refer to [Device Redundancy Groups](deviceredundancygroup.md) model documentation.

+++ 2.2.0
    The [Software Version](softwareversion.md) model has been introduced to represent the software version that is currently installed on a device. An optional software version field has been added to devices.

+++ 2.3.0
    Components from [modules](module.md) installed in [module bays](modulebay.md) on the device will also be shown in the device component lists. This includes modules that are in nested module bays. Device primary IP address can be designated from interfaces installed in modules.

## Module Tree Tab

+++ 2.4.32

For modular devices (any device with one or more [module bays](modulebay.md)), the device detail view exposes a **Module Tree** tab in addition to the existing **Module Bays** tab. While Module Bays renders a flat table of all bays on the device, Module Tree renders the full hierarchy of [Module Bays](modulebay.md) and their installed [Modules](module.md) as a single collapsible, indented tree:

- Each top-level Module Bay appears as a root row, with its installed Module (or an *Empty* indicator) on the same row.
- Modules that themselves contain Module Bays (for example, a line card with SFP slots) expand into nested rows for each of their bays — recursively, to whatever depth the device's hardware actually has.
- Each row shows the bay name, installed module type, status, role, and serial / asset tag, with hyperlinks to the corresponding Module Bay and Module detail views.
- **Expand All** and **Collapse All** buttons in the panel header, plus a per-bay toggle, let you focus on a specific subtree without scrolling through unrelated branches.

The tab is hidden when the device has no module bays, so non-modular devices remain unaffected. Viewing the tab requires `dcim.view_device`, `dcim.view_modulebay`, and `dcim.view_module` permissions.

## Developer API

The `Device` Django model class supports a method called `create_components()`. This method is normally called during `device_instance.save()`, which is called whenever you save create a Device via the GUI or the REST API, but if you are working directly in the ORM and encounter one of the two following scenarios, `device_instance.save()` is not called:

- Usage of `device_instance.objects.bulk_create()` to perform a bulk creation of Device objects
- Usage of `device_instance.save()` during handling of the `nautobot_database_ready` signal (which uses [historical models](https://docs.djangoproject.com/en/3.2/topics/migrations/#historical-models))

In these cases you will have to manually run `device_instance.create_components()` in order to instantiate the [device type's](devicetype.md) component templates (interfaces, power ports, etc.).

+++ 2.4.32
    `Device.get_module_tree()` returns a nested list of `{"bay": ModuleBay, "module": Module|None, "children": [...]}` dicts representing the device's full Module Bay / Module hierarchy. Each `children` entry uses the same shape and recurses to whatever depth the device's hardware has. Top-level bays (those attached directly to the device rather than to an installed module) appear as the outer list. Devices with no module bays return an empty list. This is the data backing the [Module Tree tab](#module-tree-tab); App authors can call it directly when they need the same hierarchical view in their own UIs or jobs.
