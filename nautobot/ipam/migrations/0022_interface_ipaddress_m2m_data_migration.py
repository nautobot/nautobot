from django.db import migrations
import netaddr


def migrate_ipaddress_to_m2m(apps, schema_editor):
    IPAddress = apps.get_model("ipam", "IPAddress")
    IPAddressToInterface = apps.get_model("ipam", "IPAddressToInterface")
    ContentType = apps.get_model("contenttypes", "ContentType")
    Interface = apps.get_model("dcim", "Interface")
    Device = apps.get_model("dcim", "Device")
    VMInterface = apps.get_model("virtualization", "VMInterface")
    VirtualMachine = apps.get_model("virtualization", "VirtualMachine")

    for ip_address in IPAddress.objects.filter(assigned_object_id__isnull=False):
        related_ct = ContentType.objects.get(id=ip_address.assigned_object_type)
        if related_ct.app_label == "dcim" and related_ct.model == "Interface":
            related_obj = Interface.objects.get(id=ip_address.assigned_object_id)
            parent = Device.objects.get(id=related_obj.device)
            m2m = IPAddressToInterface.objects.create(
                ip_address=ip_address.id,
                interface=ip_address.assigned_object_id,
            )
        elif related_ct.app_label == "virtualization" and related_ct.model == "VMInterface":
            related_obj = VMInterface.objects.get(id=ip_address.assigned_object_id)
            parent = VirtualMachine.objects.get(id=related_obj.virtual_machine)
            m2m = IPAddressToInterface.objects.create(
                ip_address=ip_address.id,
                vm_interface=ip_address.assigned_object_id,
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
            m2m.primary_for_parent = True
            m2m.save()


class Migration(migrations.Migration):

    dependencies = [
        ("dcim", "0035_related_name_changes"),
        ("virtualization", "0018_related_name_changes"),
        ("ipam", "0021_interface_to_ipaddress_m2m"),
    ]

    operations = [
        migrations.RunPython(
            code=migrate_ipaddress_to_m2m,
            reverse_code=migrations.operations.special.RunPython.noop,
        ),
    ]
