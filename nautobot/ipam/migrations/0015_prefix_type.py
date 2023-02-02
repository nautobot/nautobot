from django.core.exceptions import ObjectDoesNotExist
from django.db import migrations, models

from nautobot.core.choices import ColorChoices
from nautobot.ipam import choices


def set_prefix_type(apps, schema_editor):

    Prefix = apps.get_model("ipam", "Prefix")
    Status = apps.get_model("extras", "Status")
    ContentType = apps.get_model("contenttypes", "ContentType")
    prefix_ct = ContentType.objects.get_for_model(Prefix)

    try:
        prefix_default_status = Status.objects.get(content_types=prefix_ct, slug="active")
    except ObjectDoesNotExist:
        prefix_default_status = Status.objects.filter(content_types=prefix_ct).exclude(slug="container").first()

    # Set Prefix.type to container for prefixes with status of container
    print(f"Converting Prefixes with status=container to type=container and status={prefix_default_status.slug}")
    Prefix.objects.filter(status__slug="container").update(
        status=prefix_default_status,
        type=choices.PrefixTypeChoices.TYPE_CONTAINER,
    )

    # Set Prefix.type to pool for prefixes with `is_pool=True`
    print("Converting Prefixes with is_pool=True to type=pool")
    Prefix.objects.filter(is_pool=True).update(type=choices.PrefixTypeChoices.TYPE_POOL)

    # Remove Prefix from container status and delete the status object if no other models are related
    if Status.objects.filter(slug="container").exists():
        status_container = Status.objects.get(slug="container")
        status_container.content_types.remove(prefix_ct)
        if not status_container.content_types.exists():
            print("Removing unused Status: 'container'")
            status_container.delete()


def revert_prefix_type(apps, schema_editor):

    Prefix = apps.get_model("ipam", "Prefix")
    Status = apps.get_model("extras", "Status")
    ContentType = apps.get_model("contenttypes", "ContentType")
    prefix_ct = ContentType.objects.get_for_model(Prefix)

    # Create container status
    status_container, _ = Status.objects.get_or_create(
        slug="container",
        defaults={"name": "Container", "color": ColorChoices.COLOR_GREY},
    )
    status_container.content_types.add(prefix_ct)

    print("Converting Prefixes with type=pool to is_pool=True")
    Prefix.objects.filter(type=choices.PrefixTypeChoices.TYPE_POOL).update(is_pool=True)

    print("Converting Prefixes with type=container to status=container")
    Prefix.objects.filter(type=choices.PrefixTypeChoices.TYPE_CONTAINER).update(status=status_container)


class Migration(migrations.Migration):

    dependencies = [
        ("ipam", "0014_rename_foreign_keys_and_related_names"),
    ]

    operations = [
        migrations.AddField(
            model_name="prefix",
            name="type",
            field=models.CharField(default="network", max_length=50),
        ),
        migrations.RunPython(set_prefix_type, reverse_code=revert_prefix_type),
        migrations.RemoveField(
            model_name="prefix",
            name="is_pool",
        ),
    ]
