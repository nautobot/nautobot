from django.db import migrations


def migrate_ipaddress_to_m2m(apps, schema_editor):
    IPAddress = apps.get_model("ipam", "IPAddress")
    IPAddressToInterface = apps.get_model("ipam", "IPAddressToInterface")
    Interface = apps.get_model("dcim", "Interface")
    VMInterface = apps.get_model("virtualization", "VMInterface")

    for ip_address in IPAddress.objects.filter(assigned_object_id__isnull=False):
        related_ct = ip_address.assigned_object_type
        if related_ct.app_label == "dcim" and related_ct.model == "interface":
            related_obj = Interface.objects.get(id=ip_address.assigned_object_id)
            IPAddressToInterface.objects.create(
                ip_address=ip_address,
                interface=related_obj,
            )
        elif related_ct.app_label == "virtualization" and related_ct.model == "vminterface":
            related_obj = VMInterface.objects.get(id=ip_address.assigned_object_id)
            IPAddressToInterface.objects.create(
                ip_address=ip_address,
                vm_interface=related_obj,
            )
        else:
            continue


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
