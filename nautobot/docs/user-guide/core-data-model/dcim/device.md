# Devices

Every piece of hardware which is installed within a location or rack exists in Nautobot as a device. Devices are measured in rack units (U) and can be half depth or full depth. A device may have a height of 0U: These devices do not consume vertical rack space and cannot be assigned to a particular rack unit. A common example of a 0U device is a vertically-mounted PDU.

When assigning a multi-U device to a rack, it is considered to be mounted in the lowest-numbered rack unit which it occupies. For example, a 3U device which occupies U8 through U10 is said to be mounted in U8. This logic applies to racks with both ascending and descending unit numbering.

A device is said to be full-depth if its installation on one rack face prevents the installation of any other device on the opposite face within the same rack unit(s). This could be either because the device is physically too deep to allow a device behind it, or because the installation of an opposing device would impede airflow.

Each device must be instantiated from a pre-created device type, and its default components (console ports, power ports, interfaces, etc.) will be created automatically. (The device type associated with a device may be changed after its creation, however its components will not be updated retroactively.)

Each device must be assigned a location, device role, and operational [`status`](../../platform-functionality/status.md), and may optionally be assigned to a rack within a location. A platform, serial number, and asset tag may optionally be assigned to each device.

Device names must be unique within a location, unless the device has been assigned to a tenant. Devices may also be unnamed.

When a device has one or more interfaces with IP addresses assigned, a primary IP for the device can be designated, for both IPv4 and IPv6.

+/- 2.0.0
    In Nautobot 1.x, it was not possible to delete an IPAddress or an Interface that was serving as the primary IP address (`primary_ip4`/`primary_ip6`) for a Device. As of Nautobot 2.0, this is now permitted; doing so will clear out the Device's corresponding primary IP value.

For Devices forming a group (Failover, Load-Sharing, Redundacy or similar) refer to [Device Redundancy Groups](deviceredundancygroup.md) model documentation.

## Developer API

The `Device` Django model class supports a method called `create_components()`. This method is normally called during `device_instance.save()`, which is called whenever you save create a Device via the GUI or the REST API, but if you are working directly in the ORM and encounter one of the two following scenarios, `device_instance.save()` is not called:

- Usage of `device_instance.objects.bulk_create()` to perform a bulk creation of Device objects
- Usage of `device_instance.save()` during handling of the `nautobot_database_ready` signal (which uses [historical models](https://docs.djangoproject.com/en/3.2/topics/migrations/#historical-models))

In these cases you will have to manually run `device_instance.create_components()` in order to instantiate the [device type's](devicetype.md) component templates (interfaces, power ports, etc.).
