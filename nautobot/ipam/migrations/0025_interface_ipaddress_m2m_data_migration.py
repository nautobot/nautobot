from django.db import migrations
import netaddr


def migrate_ipaddress_to_m2m(apps, schema_editor):
    IPAddress = apps.get_model("ipam", "IPAddress")
    IPAddressToInterface = apps.get_model("ipam", "IPAddressToInterface")
    Interface = apps.get_model("dcim", "Interface")
    Device = apps.get_model("dcim", "Device")
    VMInterface = apps.get_model("virtualization", "VMInterface")
    VirtualMachine = apps.get_model("virtualization", "VirtualMachine")

    for ip_address in IPAddress.objects.filter(assigned_object_id__isnull=False):
        related_ct = ip_address.assigned_object_type
        if related_ct.app_label == "dcim" and related_ct.model == "interface":
            related_obj = Interface.objects.get(id=ip_address.assigned_object_id)
            parent = Device.objects.get(id=related_obj.device_id)
            m2m = IPAddressToInterface.objects.create(
                ip_address=ip_address,
                interface=related_obj,
            )
        elif related_ct.app_label == "virtualization" and related_ct.model == "vminterface":
            related_obj = VMInterface.objects.get(id=ip_address.assigned_object_id)
            parent = VirtualMachine.objects.get(id=related_obj.virtual_machine_id)
            m2m = IPAddressToInterface.objects.create(
                ip_address=ip_address,
                vm_interface=related_obj,
            )
        else:
            continue

        address = netaddr.IPNetwork(f"{ip_address.host}/{ip_address.prefix_length}")
        if (
            address.version == 4
            and parent.primary_ip4_id == ip_address.id
            or address.version == 6
            and parent.primary_ip6_id == ip_address.id
        ):
            m2m.primary_for_device = True
            m2m.save()


class Migration(migrations.Migration):

    dependencies = [
        ("ipam", "0024_interface_to_ipaddress_m2m"),
    ]

    operations = [
        migrations.RunPython(
            code=migrate_ipaddress_to_m2m,
            reverse_code=migrations.operations.special.RunPython.noop,
        ),
    ]
