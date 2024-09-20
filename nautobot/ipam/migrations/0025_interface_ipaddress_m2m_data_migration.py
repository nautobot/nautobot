from contextlib import suppress

from django.db import migrations


def migrate_ipaddress_to_m2m(apps, schema_editor):
    IPAddress = apps.get_model("ipam", "IPAddress")
    IPAddressToInterface = apps.get_model("ipam", "IPAddressToInterface")
    Interface = apps.get_model("dcim", "Interface")
    VMInterface = apps.get_model("virtualization", "VMInterface")

    for ip_address in IPAddress.objects.filter(assigned_object_id__isnull=False, assigned_object_type__isnull=False):
        related_ct = ip_address.assigned_object_type
        if related_ct.app_label == "dcim" and related_ct.model == "interface":
            with suppress(Interface.DoesNotExist):
                related_obj = Interface.objects.get(id=ip_address.assigned_object_id)
                IPAddressToInterface.objects.create(
                    ip_address=ip_address,
                    interface=related_obj,
                )
        elif related_ct.app_label == "virtualization" and related_ct.model == "vminterface":
            with suppress(VMInterface.DoesNotExist):
                related_obj = VMInterface.objects.get(id=ip_address.assigned_object_id)
                IPAddressToInterface.objects.create(
                    ip_address=ip_address,
                    vm_interface=related_obj,
                )


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0001_initial_part_1"),
        ("ipam", "0024_interface_to_ipaddress_m2m"),
        ("virtualization", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            code=migrate_ipaddress_to_m2m,
            reverse_code=migrations.operations.special.RunPython.noop,
        ),
    ]
