from datetime import datetime, time
import uuid

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import migrations
from django.utils.timezone import make_aware

from nautobot.core.models.generics import _NautobotTaggableManager
from nautobot.core.models.utils import serialize_object
from nautobot.extras import choices as extras_choices
from nautobot.extras import models as extras_models
from nautobot.extras.constants import CHANGELOG_MAX_OBJECT_REPR
from nautobot.ipam.choices import PrefixTypeChoices


def migrate_aggregate_to_prefix(apps, schema_editor):

    Aggregate = apps.get_model("ipam", "Aggregate")
    ContentType = apps.get_model("contenttypes", "ContentType")
    Prefix = apps.get_model("ipam", "Prefix")
    ObjectChange = apps.get_model("extras", "ObjectChange")
    Status = apps.get_model("extras", "Status")
    Tag = apps.get_model("extras", "Tag")
    TaggedItem = apps.get_model("extras", "TaggedItem")

    aggregate_ct = ContentType.objects.get_for_model(Aggregate)
    prefix_ct = ContentType.objects.get_for_model(Prefix)

    try:
        prefix_default_status = Status.objects.get(content_types=prefix_ct, slug="active")
    except ObjectDoesNotExist:
        prefix_default_status = Status.objects.filter(content_types=prefix_ct).first()

    # add prefix content type to any existing aggregate tags
    for tag in Tag.objects.filter(content_types=aggregate_ct):
        tag.content_types.add(prefix_ct)

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
            if prefix.type != PrefixTypeChoices.TYPE_CONTAINER:
                mismatches["type"] = PrefixTypeChoices.TYPE_CONTAINER
            error_message = (
                "\n",
                f"Unable to migrate all fields from Aggregate {instance.network}/{instance.prefix_length} to Prefix due to an existing Prefix.",
                f"Some of the following data may have to be migrated manually: {mismatches}",
            )
            if mismatches:
                print(" ".join(error_message), flush=True)

        else:
            prefix = Prefix.objects.create(
                broadcast=instance.broadcast,
                date_allocated=date_allocated,
                description=instance.description,
                network=instance.network,
                prefix_length=instance.prefix_length,
                rir=instance.rir,
                status=prefix_default_status,
                tenant=instance.tenant,
                type=PrefixTypeChoices.TYPE_CONTAINER,
            )

        # move tags from aggregate to prefix
        for tagged_item in TaggedItem.objects.filter(content_type=aggregate_ct, object_id=instance.pk):
            if TaggedItem.objects.filter(
                content_type=prefix_ct, object_id=prefix.pk, tag_id=tagged_item.tag_id
            ).exists():
                tagged_item.delete()
            else:
                tagged_item.content_type = prefix_ct
                tagged_item.object_id = prefix.pk
                tagged_item.save()

        # update any object changes related to prior aggregate instance
        ObjectChange.objects.filter(changed_object_type=aggregate_ct, changed_object_id=instance.pk).update(
            changed_object_type=prefix_ct, changed_object_id=prefix.pk
        )
        ObjectChange.objects.filter(related_object_type=aggregate_ct, related_object_id=instance.pk).update(
            related_object_type=prefix_ct, related_object_id=prefix.pk
        )

        # make tag manager available in migration
        # https://github.com/jazzband/django-taggit/issues/101
        # https://github.com/jazzband/django-taggit/issues/454
        prefix.tags = _NautobotTaggableManager(
            through=extras_models.TaggedItem, model=Prefix, instance=prefix, prefetch_cache_name="tags"
        )

        # create an object change to document migration
        ObjectChange.objects.create(
            action=extras_choices.ObjectChangeActionChoices.ACTION_UPDATE,
            change_context=extras_choices.ObjectChangeEventContextChoices.CONTEXT_ORM,
            change_context_detail="Migrated from Aggregate",
            changed_object_id=prefix.pk,
            changed_object_type=prefix_ct,
            object_data=serialize_object(prefix),
            object_repr=f"{prefix.network}/{prefix.prefix_length}"[:CHANGELOG_MAX_OBJECT_REPR],
            request_id=uuid.uuid4(),
        )


class Migration(migrations.Migration):

    dependencies = [
        ("ipam", "0020_prefix_add_rir_and_date_allocated"),
        ("extras", "0039_objectchange__add_change_context"),
    ]

    operations = [
        migrations.RunPython(migrate_aggregate_to_prefix),
    ]
