from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import migrations

from nautobot.users.models import ObjectPermission


def add_default_groups(apps, schema_editor):
    read_only, _ = Group.objects.get_or_create(name="Read Only")
    admin, _ = Group.objects.get_or_create(name="Admins")

    ro_obj_permission, created = ObjectPermission.objects.get_or_create(
        name="Default: Global Read Only",
        actions=["view"],
    )

    if not created:
        # Only exit if it didn't exist before
        return

    rw_obj_permission, created = ObjectPermission.objects.get_or_create(
        name="Default: Global Read/Write",
        actions=["view", "add", "change", "delete"],
    )

    if not created:
        return

    ro_obj_permission.groups.add(read_only)
    rw_obj_permission.groups.add(admin)

    # Get all ContentTypes and add them to Permissions
    for x in ContentType.objects.all():
        ro_obj_permission.object_types.add(x)
        rw_obj_permission.object_types.add(x)


def remove_default_groups(apps, schema_editor):
    try:
        read_only = Group.objects.get(name="Default: Global Read Only")
        read_only.delete()
    except ObjectDoesNotExist:
        pass

    try:
        admin = Group.objects.get(name="Default: Global Read/Write")
        admin.delete()
    except ObjectDoesNotExist:
        pass

    try:
        read_only = ObjectPermission.objects.get(name="Default: Global Read Only")
        read_only.delete()
    except ObjectDoesNotExist:
        pass

    try:
        admin = ObjectPermission.objects.get_or_create(name="Default: Global Read/Write")
        admin.delete()
    except ObjectDoesNotExist:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0010_user_default_saved_views"),
    ]

    operations = [migrations.RunPython(add_default_groups, remove_default_groups)]
