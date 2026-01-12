from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db.models.signals import m2m_changed, pre_delete, pre_save
from django.dispatch import receiver

from nautobot.ipam.models import (
    IPAddress,
    IPAddressToInterface,
    Prefix,
    PrefixLocationAssignment,
    VLANLocationAssignment,
    VRF,
    VRFDeviceAssignment,
    VRFPrefixAssignment,
)


@receiver(pre_save, sender=VRFDeviceAssignment)
@receiver(pre_save, sender=VRFPrefixAssignment)
def ipam_object_saved(sender, instance, raw=False, **kwargs):
    """
    Forcibly call `full_clean()` when a new IPAM intermediate model is manually saved to prevent
    creation of invalid objects.
    """
    if raw:
        return
    instance.full_clean()


@receiver(m2m_changed, sender=VRFPrefixAssignment)
def vrf_prefix_associated(sender, instance, action, reverse, model, pk_set, **kwargs):
    """
    Disallow adding Prefixes if the namespace doesn't match.
    """

    if action == "pre_add":
        prefixes = model.objects.filter(pk__in=pk_set).exclude(namespace=instance.namespace)
        if prefixes.exists():
            raise ValidationError({"prefixes": "Prefix must match namespace of VRF"})


@receiver(m2m_changed, sender=VRFDeviceAssignment)
def vrf_device_associated(sender, instance, action, reverse, model, pk_set, **kwargs):
    """
    Assert validation on m2m when devices are associated with a VRF.
    """

    # TODO(jathan): Temporary workaround until a formset to add/remove/update VRFs <-> Devices and
    # optionally setting RD/name on assignment. k
    if action == "post_add":
        if isinstance(instance, VRF):
            for assignment in instance.device_assignments.iterator():
                assignment.validated_save()
        else:
            for assignment in instance.vrf_assignments.iterator():
                assignment.validated_save()


@receiver(pre_delete, sender=IPAddressToInterface)
def ip_address_to_interface_pre_delete(instance, raw=False, **kwargs):
    if raw:
        return

    # Check if the removed IPAddressToInterface instance contains an IPAddress
    # that is the primary_v{version} of the host machine.

    if getattr(instance, "interface"):
        host = instance.interface.parent
        other_assignments_exist = (
            IPAddressToInterface.objects.filter(interface__in=host.all_interfaces, ip_address=instance.ip_address)
            .exclude(id=instance.id)
            .exists()
        )
    else:
        host = instance.vm_interface.virtual_machine
        other_assignments_exist = (
            IPAddressToInterface.objects.filter(vm_interface__virtual_machine=host, ip_address=instance.ip_address)
            .exclude(id=instance.id)
            .exists()
        )

    # Only nullify the primary_ip field if no other interfaces/vm_interfaces have the ip_address
    host_needs_save = False
    if not other_assignments_exist and instance.ip_address == host.primary_ip4:
        host.primary_ip4 = None
        host_needs_save = True
    elif not other_assignments_exist and instance.ip_address == host.primary_ip6:
        host.primary_ip6 = None
        host_needs_save = True

    if host_needs_save:
        host.save()


@receiver(pre_save, sender=IPAddressToInterface)
def ip_address_to_interface_assignment_created(sender, instance, raw=False, **kwargs):
    """
    Forcibly call `full_clean()` when a new `IPAddressToInterface` object
    is manually created to prevent inadvertantly creating invalid IPAddressToInterface.
    """
    if raw:
        return

    instance.full_clean()


@receiver(m2m_changed, sender=PrefixLocationAssignment)
@receiver(m2m_changed, sender=VLANLocationAssignment)
def assert_locations_content_types(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action != "pre_add":
        return
    if not reverse:
        # Adding a Location to a Prefix or VLAN
        # instance = the Prefix or VLAN
        # model = Location class
        instance_ct = ContentType.objects.get_for_model(instance)
        invalid_locations = (
            model.objects.without_tree_fields()
            .select_related("location_type")
            .filter(Q(pk__in=pk_set), ~Q(location_type__content_types__in=[instance_ct]))
        )
        if invalid_locations.exists():
            invalid_location_types = {location.location_type.name for location in invalid_locations}
            label = "Prefixes" if isinstance(instance, Prefix) else "VLANs"
            raise ValidationError(
                {"locations": f"{label} may not associate to Locations of types {list(invalid_location_types)}."}
            )
    else:
        # Adding a Prefix or a VLAN to a Location
        # instance = the Location
        # model = Prefix or VLAN class
        model_ct = ContentType.objects.get_for_model(model)
        key = "prefixes" if model is Prefix else "vlans"
        label = "Prefixes" if model is Prefix else "VLANs"
        if model_ct not in instance.location_type.content_types.all():
            raise ValidationError(
                {key: f"{instance} is a {instance.location_type} and may not have {label} associated to it."}
            )


def _validate_interface_ipaddress_assignments(sender, instance, pk_set, interface_field):
    """
    Helper function to validate IPAddressToInterface instances on Interface and VMInterface objects after M2M operations.

    For example:
        * interface.ip_addresses.add(ip_address)
        * vm_interface.ip_addresses.add(ip_address)

    Args:
        sender: The through model class (IPAddressToInterface)
        instance: The interface instance (Interface or VMInterface)
        pk_set: Set of IP address PKs being modified
        interface_field: Field name to filter on ('interface' or 'vm_interface')
    """
    # Get the through model instances that were just created
    filter_kwargs = {interface_field: instance, "ip_address_id__in": pk_set}
    through_instances = sender.objects.filter(**filter_kwargs)

    # Validate each through model instance
    for through_instance in through_instances:
        through_instance.full_clean()


def _validate_ipaddress_interface_assignments(sender, instance, pk_set, interface_model):
    """
    Helper function to validate IPAddressToInterface instances on IPAddress objects after M2M operations.

    For example:
        * ip_address.interfaces.add(interface)
        * ip_address.vm_interfaces.add(vm_interface)

    Args:
        sender: The through model class (IPAddressToInterface)
        instance: The interface instance (Interface or VMInterface)
        pk_set: Set of IP address PKs being modified
        interface_model: Field name to filter on ('interface' or 'vm_interface')
    """
    filter_kwargs = {"ip_address": instance, interface_model + "_id__in": pk_set}
    through_instances = sender.objects.filter(**filter_kwargs)
    for through_instance in through_instances:
        through_instance.full_clean()


@receiver(m2m_changed, sender=IPAddressToInterface)
def validate_interface_ip_assignments(sender, instance, action, pk_set, **kwargs):
    """
    Validate IPAddressToInterface instances after M2M operations.

    Handles both physical Interface and VMInterface IP assignments.
    Since Django's M2M add() with through_defaults bypasses save() methods,
    we validate the through model instances via signal handler.
    """
    from nautobot.dcim.models import Interface
    from nautobot.virtualization.models import VMInterface

    if action == "post_add" and pk_set:
        # Route to appropriate validation based on instance type
        if isinstance(instance, Interface):
            _validate_interface_ipaddress_assignments(sender, instance, pk_set, "interface")
        elif isinstance(instance, VMInterface):
            _validate_interface_ipaddress_assignments(sender, instance, pk_set, "vm_interface")
        elif isinstance(instance, IPAddress):
            interface_model = kwargs["model"]

            if interface_model == Interface:
                _validate_ipaddress_interface_assignments(sender, instance, pk_set, "interface")
            elif interface_model == VMInterface:
                _validate_ipaddress_interface_assignments(sender, instance, pk_set, "vm_interface")
