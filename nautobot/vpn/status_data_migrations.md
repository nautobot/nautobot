# Status Data Migrations

This document provides an example of how to create a data migration to populate status choices for the models in the `nautobot_vpn_models` app.

First, create the new empty data migration:
`nautobot-server makemigrations nautobot_vpn_models --empty`

Then copy the following code into the newly created migration file:

```python
from django.db import migrations
from nautobot.apps.choices import ColorChoices
from nautobot.extras.management import export_metadata_from_choiceset

from nautobot_vpn_models import choices
def populate_vpn_tunnel_status_choices(apps, schema_editor):
    """Populate the status choices for the VPNTunnel status field."""

    color_map = {
        # TODO INIT - Add new status choice colors, if using statuses that already exist in Nautobot, use the existing color
        "Active": ColorChoices.COLOR_GREEN,
    }
    description_map = {
        # TODO INIT - Add new status choice descriptions, if using statuses that already exist in Nautobot, use the existing description
        "Active": "Unit is active",
    }
    choices = export_metadata_from_choiceset(
        choices.VPNTunnelStatusChoices,
        color_map=color_map,
        description_map=description_map,
    )

    ContentType = apps.get_model("contenttypes", "ContentType")
    Status = apps.get_model("extras", "Status")

    content_type = ContentType.objects.get_for_model(apps.get_model("nautobot_vpn_models", "VPNTunnel"))
    for choice_kwargs in choices:
        name = choice_kwargs.pop("name")
        try:
            obj, _ = Status.objects.get_or_create(
                name=name,
                defaults=choice_kwargs,
            )
            obj.content_types.add(content_type)
        except IntegrityError as err:
            raise SystemExit(
                f"Unexpected error while creating status {name} for nautobot_vpn_models.VPNTunnel: {err}"
            ) from err

def clear_vpn_tunnel_status_choices(apps, schema_editor):
    """Clear the status choices for the VPNTunnel status field."""

    ContentType = apps.get_model("contenttypes", "ContentType")
    Status = apps.get_model("extras", "Status")

    content_type = ContentType.objects.get_for_model(apps.get_model("nautobot_vpn_models", "VPNTunnel"))
    statuses = Status.objects.filter(content_types=content_type).values_list("name", flat=True)

    for name in statuses:
        try:
            status = Status.objects.get(name=name)
            status.content_types.remove(content_type)
        except IntegrityError as err:
            raise SystemExit(
                f"Unexpected error while removing nautobot_vpn_models.VPNTunnel from status {name}: {err}"
            ) from err


```

Then add the following code to the operations list in the migration file:
    ("contenttypes", "0001_initial"),
    ("extras", "0001_initial_part_1"),

```python
migrations.RunPython(
    code=populate_vpn_tunnel_status_choices,
    reverse_code=clear_vpn_tunnel_status_choices,
),
```

Here is an example of what it might look like:

```python
class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0001_initial"),
        ("extras", "0001_initial_part_1"),
        ('nautobot_vpn_models', '0001_initial'),
    ]
operations = [
    migrations.RunPython(
        code=populate_vpn_tunnel_status_choices,
        reverse_code=clear_vpn_tunnel_status_choices,
    ),
]

```

# TODO: Add default profiles - HLD in appendix B
