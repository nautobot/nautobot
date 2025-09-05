from nautobot.apps.ui import (
    queryset_to_nested_dict_records_as_series,
)
from nautobot.circuits.models import Circuit
from nautobot.core.models.querysets import count_related
from nautobot.core.views.utils import get_obj_from_context
from nautobot.dcim.models import Controller, ControllerManagedDeviceGroup, Device, Location, Rack, RackReservation
from nautobot.extras.models import DynamicGroup
from nautobot.ipam.models import IPAddress, Prefix, VLAN, VRF
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.models import Cluster, VirtualMachine


def tenant_related_objects_data(context):
    instance = get_obj_from_context(context)
    data_series = queryset_to_nested_dict_records_as_series(
        Tenant.objects.annotate(
            Circuits=count_related(Circuit, "tenant"),
            Clusters=count_related(Cluster, "tenant"),
            Controllers=count_related(Controller, "tenant"),
            ControllerManagedDeviceGroups=count_related(ControllerManagedDeviceGroup, "tenant"),
            Devices=count_related(Device, "tenant"),
            DynamicGroups=count_related(DynamicGroup, "tenant"),
            IpAddresses=count_related(IPAddress, "tenant"),
            Locations=count_related(Location, "tenant"),
            Prefixes=count_related(Prefix, "tenant"),
            Racks=count_related(Rack, "tenant"),
            RackReservations=count_related(RackReservation, "tenant"),
            VirtualMachines=count_related(VirtualMachine, "tenant"),
            VLANs=count_related(VLAN, "tenant"),
            VRFs=count_related(VRF, "tenant"),
        ).filter(pk=instance.id),
        record_key="name",
        value_keys=[
            "Circuits",
            "Clusters",
            "Controllers",
            "ControllerManagedDeviceGroups",
            "Devices",
            "DynamicGroups",
            "IpAddresses",
            "Locations",
            "Prefixes",
            "Racks",
            "RackReservations",
            "VirtualMachines",
            "VLANs",
            "VRFs",
        ],
    )
    return data_series
