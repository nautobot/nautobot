from datetime import datetime, time

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import migrations
from django.utils.timezone import make_aware

from nautobot.ipam import choices


def migrate_aggregate_to_prefix(apps, schema_editor):

    Prefix = apps.get_model("ipam", "Prefix")
    Aggregate = apps.get_model("ipam", "Aggregate")
    Status = apps.get_model("extras", "Status")
    ObjectChange = apps.get_model("extras", "ObjectChange")
    ContentType = apps.get_model("contenttypes", "ContentType")
    aggregate_ct = ContentType.objects.get_for_model(Aggregate)
    prefix_ct = ContentType.objects.get_for_model(Prefix)

    try:
        prefix_default_status = Status.objects.get(content_types=prefix_ct, slug="active")
    except ObjectDoesNotExist:
        prefix_default_status = Status.objects.filter(content_types=prefix_ct).first()

    for instance in Aggregate.objects.all():
        # convert date to datetime
        date_allocated = instance.date_added
        if date_allocated is not None:
            date_allocated = datetime.combine(date_allocated, time.min)
            if settings.USE_TZ:
                date_allocated = make_aware(date_allocated)

        if Prefix.objects.filter(
            network=instance.network,
            prefix_length=instance.prefix_length,
            vrf__isnull=True,
        ).exists():
            # update rir and date_allocated on existing prefix
            prefix = Prefix.objects.get(network=instance.network, prefix_length=instance.prefix_length)
            prefix.rir = instance.rir
            prefix.date_allocated = date_allocated
            prefix.save()

            # if type, tenant or description don't match, print an error message
            mismatches = {}
            if instance.description != prefix.description:
                mismatches["description"] = instance.description
            if instance.tenant != prefix.tenant:
                mismatches["tenant"] = getattr(instance.tenant, "name", None)
            if prefix.type != choices.PrefixTypeChoices.TYPE_CONTAINER:
                mismatches["type"] = choices.PrefixTypeChoices.TYPE_CONTAINER
            error_message = (
                "\n",
                f"Unable to migrate all fields from Aggregate {instance.network}/{instance.prefix_length} to Prefix due to an existing Prefix.",
                f"Some of the following data may have to be migrated manually: {mismatches}",
            )
            if mismatches:
                print(" ".join(error_message), flush=True)

        else:
            prefix = Prefix.objects.create(
                network=instance.network,
                broadcast=instance.broadcast,
                prefix_length=instance.prefix_length,
                status=prefix_default_status,
                type=choices.PrefixTypeChoices.TYPE_CONTAINER,
                tenant=instance.tenant,
                description=instance.description,
                rir=instance.rir,
                date_allocated=date_allocated,
            )

        # update any object changes for prior aggregate instance
        ObjectChange.objects.filter(changed_object_type=aggregate_ct, changed_object_id=instance.pk).update(
            changed_object_type=prefix_ct, changed_object_id=prefix.pk
        )
        ObjectChange.objects.filter(related_object_type=aggregate_ct, related_object_id=instance.pk).update(
            related_object_type=prefix_ct, related_object_id=prefix.pk
        )


class Migration(migrations.Migration):

    dependencies = [
        ("ipam", "0019_prefix_add_rir_and_date_allocated"),
        ("extras", "0001_initial_part_1"),
    ]

    operations = [
        migrations.RunPython(migrate_aggregate_to_prefix),
    ]
