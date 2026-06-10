from django.db import migrations

from nautobot.core.choices import ColorChoices

# Starter roles for IPRange.
IPRANGE_ROLES = [
    {"name": "DHCP", "color": ColorChoices.COLOR_BLUE},
    {"name": "Firewall Object", "color": ColorChoices.COLOR_RED},
    {"name": "NAT Pool", "color": ColorChoices.COLOR_ORANGE},
    {"name": "LB Pool", "color": ColorChoices.COLOR_GREEN},
    {"name": "Reserved", "color": ColorChoices.COLOR_GREY},
]


def create_iprange_roles(apps, schema_editor):
    Role = apps.get_model("extras", "Role")
    ContentType = apps.get_model("contenttypes", "ContentType")
    iprange_ct, _ = ContentType.objects.get_or_create(
        app_label="ipam",
        model="iprange",
    )

    for role_data in IPRANGE_ROLES:
        role, _ = Role.objects.get_or_create(
            name=role_data["name"],
            defaults={"color": role_data["color"]},
        )
        role.content_types.add(iprange_ct)


def remove_iprange_roles(apps, schema_editor):
    Role = apps.get_model("extras", "Role")
    ContentType = apps.get_model("contenttypes", "ContentType")

    iprange_ct, _ = ContentType.objects.get_or_create(
        app_label="ipam",
        model="iprange",
    )

    for role_data in IPRANGE_ROLES:
        try:
            role = Role.objects.get(name=role_data["name"])
        except Role.DoesNotExist:
            continue
        role.content_types.remove(iprange_ct)
        # Delete the role only if it's no longer tied to any content type.
        if not role.content_types.exists():
            role.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("ipam", "0056_iprange"),
    ]

    operations = [
        migrations.RunPython(create_iprange_roles, remove_iprange_roles),
    ]
