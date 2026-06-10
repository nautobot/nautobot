"""Shared test utilities for the vpn module."""

from nautobot.dcim.choices import InterfaceTypeChoices
from nautobot.dcim.factory import DeviceFactory
from nautobot.dcim.models import Interface
from nautobot.ipam.models import VLAN, VLANGroup
from nautobot.tenancy.factory import TenantFactory
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.factory import ClusterFactory, ClusterTypeFactory, VirtualMachineFactory
from nautobot.virtualization.models import VMInterface
from nautobot.vpn import models
from nautobot.vpn.factory import get_status_for_model


class VPNTerminationFixtureMixin:
    """Helpers for creating deterministic termination-related fixtures."""

    @classmethod
    def _available_interfaces(cls):
        used = models.VPNTermination.objects.exclude(interface__isnull=True).values_list("interface_id", flat=True)
        return Interface.objects.exclude(pk__in=used).filter(device__isnull=False)

    @classmethod
    def _ensure_available_interfaces(cls, count):
        interfaces = list(cls._available_interfaces()[:count])
        while len(interfaces) < count:
            device = DeviceFactory.create()
            Interface.objects.create(
                device=device,
                name=f"{cls.__name__}-if-{Interface.objects.count()}",
                status=get_status_for_model(Interface),
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            )
            interfaces = list(cls._available_interfaces()[:count])
        return interfaces

    @classmethod
    def _available_vlans(cls):
        used = models.VPNTermination.objects.exclude(vlan__isnull=True).values_list("vlan_id", flat=True)
        return VLAN.objects.exclude(pk__in=used)

    @classmethod
    def _ensure_available_vlans(cls, count):
        vlans = list(cls._available_vlans()[:count])
        while len(vlans) < count:
            vlan_group, _ = VLANGroup.objects.get_or_create(name=f"{cls.__name__} VLAN Group")
            next_vid = max(VLAN.objects.values_list("vid", flat=True), default=4095) + 1
            VLAN.objects.create(
                vid=next_vid,
                name=f"{cls.__name__} VLAN {next_vid}",
                status=get_status_for_model(VLAN),
                vlan_group=vlan_group,
            )
            vlans = list(cls._available_vlans()[:count])
        return vlans

    @classmethod
    def _available_vm_interfaces(cls):
        used = models.VPNTermination.objects.exclude(vm_interface__isnull=True).values_list(
            "vm_interface_id", flat=True
        )
        return VMInterface.objects.exclude(pk__in=used)

    @classmethod
    def _ensure_available_vm_interfaces(cls, count):
        vm_interfaces = list(cls._available_vm_interfaces()[:count])
        while len(vm_interfaces) < count:
            cluster_type = ClusterTypeFactory.create()
            cluster = ClusterFactory.create(cluster_type=cluster_type)
            virtual_machine = VirtualMachineFactory.create(cluster=cluster)
            VMInterface.objects.create(
                virtual_machine=virtual_machine,
                name=f"{cls.__name__}-vmif-{VMInterface.objects.count()}",
                status=get_status_for_model(VMInterface),
            )
            vm_interfaces = list(cls._available_vm_interfaces()[:count])
        return vm_interfaces

    @classmethod
    def _ensure_tenant(cls):
        return Tenant.objects.first() or TenantFactory.create()
