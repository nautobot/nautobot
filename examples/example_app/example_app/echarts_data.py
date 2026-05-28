from nautobot.core.views.utils import get_obj_from_context


def tenant_related_objects_data(context):
    instance = get_obj_from_context(context)
    data_series = {
        "Circuits": instance.circuits.count(),
        "Clusters": instance.clusters.count(),
        "Controllers": instance.controllers.count(),
        "ControllerManagedDeviceGroups": instance.controller_managed_device_groups.count(),
        "Devices": instance.devices.count(),
        "DynamicGroups": instance.dynamic_groups.count(),
        "IpAddresses": instance.ip_addresses.count(),
        "Locations": instance.locations.count(),
        "Prefixes": instance.prefixes.count(),
        "Racks": instance.racks.count(),
        "RackReservations": instance.rack_reservations.count(),
        "VirtualMachines": instance.virtual_machines.count(),
        "VLANs": instance.vlans.count(),
        "VRFs": instance.vrfs.count(),
    }
    return {instance.name: data_series}
