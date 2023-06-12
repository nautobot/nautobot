from datetime import datetime, time
import uuid

from django.conf import settings
from django.db import migrations
from django.utils.timezone import make_aware

from nautobot.core.models.managers import TagsManager
from nautobot.core.models.utils import serialize_object
from nautobot.extras import choices as extras_choices
from nautobot.extras import models as extras_models
from nautobot.extras.constants import CHANGELOG_MAX_OBJECT_REPR
from nautobot.ipam.choices import PrefixTypeChoices


def _convert_date_to_datetime(date):
    """Convert date object to datetime object and add timezone if django USE_TZ=True"""
    if date is not None:
        date = datetime.combine(date, time.min)
        if settings.USE_TZ:
            return make_aware(date)
    return date


def _migrate_aggregate_to_existing_prefix(aggregate, prefix):
    # update rir and date_allocated on existing prefix
    prefix.rir = aggregate.rir
    prefix.date_allocated = _convert_date_to_datetime(aggregate.date_added)
    prefix.save()

    # if type, tenant or description don't match, print an error message
    mismatches = {}
    if aggregate.description != prefix.description:
        mismatches["description"] = aggregate.description
    if aggregate.tenant != prefix.tenant:
        mismatches["tenant"] = getattr(aggregate.tenant, "name", None)
    if prefix.type != PrefixTypeChoices.TYPE_CONTAINER:
        mismatches["type"] = PrefixTypeChoices.TYPE_CONTAINER
    return mismatches


def _migrate_aggregate_notes_to_prefix(apps, aggregate, aggregate_ct, prefix_ct):
    Note = apps.get_model("extras", "Note")
    Note.objects.filter(assigned_object_type=aggregate_ct, assigned_object_id=aggregate.id).update(
        assigned_object_type=prefix_ct,
        assigned_object_id=aggregate.migrated_to_prefix_id,
    )


def _migrate_aggregate_object_changes_to_prefix(apps, aggregate, aggregate_ct, prefix_ct):
    ObjectChange = apps.get_model("extras", "ObjectChange")

    # migrate ObjectChanges where changed_object_type is aggregate
    ObjectChange.objects.filter(changed_object_type=aggregate_ct, changed_object_id=aggregate.id).update(
        changed_object_type=prefix_ct,
        changed_object_id=aggregate.migrated_to_prefix_id,
    )

    # migrate ObjectChanges where related_object_type is aggregate
    ObjectChange.objects.filter(related_object_type=aggregate_ct, related_object_id=aggregate.id).update(
        related_object_type=prefix_ct,
        related_object_id=aggregate.migrated_to_prefix_id,
    )


def _migrate_aggregate_tags_to_prefix(apps, aggregate, aggregate_ct, prefix_ct):
    TaggedItem = apps.get_model("extras", "TaggedItem")
    prefix_id = aggregate.migrated_to_prefix_id
    for tagged_item in TaggedItem.objects.filter(content_type=aggregate_ct, object_id=aggregate.id):
        if TaggedItem.objects.filter(content_type=prefix_ct, object_id=prefix_id, tag_id=tagged_item.tag_id).exists():
            tagged_item.delete()
        else:
            tagged_item.content_type = prefix_ct
            tagged_item.object_id = prefix_id
            tagged_item.save()


def _migrate_aggregate_custom_fields_to_prefix(aggregate):
    mismatches = {}
    prefix = aggregate.migrated_to_prefix
    for key, value in aggregate._custom_field_data.items():
        if key in prefix._custom_field_data and prefix._custom_field_data[key] != value:
            mismatches[key] = value
        else:
            prefix._custom_field_data[key] = value
    prefix.save()
    if mismatches:
        mismatches = {"_custom_field_data": mismatches}
    return mismatches


def _migrate_aggregate_relationships_to_prefix(apps, aggregate, aggregate_ct, prefix_ct):
    RelationshipAssociation = apps.get_model("extras", "RelationshipAssociation")
    prefix_id = aggregate.migrated_to_prefix_id
    RelationshipAssociation.objects.filter(source_type=aggregate_ct, source_id=aggregate.id).update(
        source_type=prefix_ct,
        source_id=prefix_id,
    )
    RelationshipAssociation.objects.filter(destination_type=aggregate_ct, destination_id=aggregate.id).update(
        destination_type=prefix_ct,
        destination_id=prefix_id,
    )


def migrate_aggregate_to_prefix(apps, schema_editor):
    Aggregate = apps.get_model("ipam", "Aggregate")
    ContentType = apps.get_model("contenttypes", "ContentType")
    ComputedField = apps.get_model("extras", "ComputedField")
    CustomField = apps.get_model("extras", "CustomField")
    CustomLink = apps.get_model("extras", "CustomLink")
    Prefix = apps.get_model("ipam", "Prefix")
    ObjectChange = apps.get_model("extras", "ObjectChange")
    ObjectPermission = apps.get_model("users", "ObjectPermission")
    Relationship = apps.get_model("extras", "relationship")
    Status = apps.get_model("extras", "Status")
    Tag = apps.get_model("extras", "Tag")

    aggregate_ct = ContentType.objects.get_for_model(Aggregate)
    prefix_ct = ContentType.objects.get_for_model(Prefix)

    mismatches = {}

    # aggregate does not have status; select/create a default status for migrated aggregates
    if Status.objects.filter(content_types=prefix_ct, slug="active").exists():
        prefix_default_status = Status.objects.get(content_types=prefix_ct, slug="active")
    elif Status.objects.filter(content_types=prefix_ct).exists():
        prefix_default_status = Status.objects.filter(content_types=prefix_ct).first()
    else:
        prefix_default_status = Status.objects.create(name="Active", slug="active")
        prefix_default_status.content_types.add(prefix_ct)

    # add prefix content type to any existing aggregate tags
    for tag in Tag.objects.filter(content_types=aggregate_ct):
        tag.content_types.add(prefix_ct)

    # migrate Aggregate ObjectPermissions to Prefix
    for object_permission in ObjectPermission.objects.filter(object_types=aggregate_ct):
        object_permission.object_types.add(prefix_ct)

    # migrate Aggregate CustomFields to Prefix
    for custom_field in CustomField.objects.filter(content_types=aggregate_ct):
        custom_field.content_types.add(prefix_ct)

    # migrate Aggregate CustomLinks to Prefix
    CustomLink.objects.filter(content_type=aggregate_ct).update(content_type=prefix_ct)

    # migrate Aggregate ComputedFields to Prefix
    ComputedField.objects.filter(content_type=aggregate_ct).update(content_type=prefix_ct)

    # migrate Aggregate Relationships to Prefix
    Relationship.objects.filter(source_type=aggregate_ct).update(source_type=prefix_ct)
    Relationship.objects.filter(destination_type=aggregate_ct).update(destination_type=prefix_ct)

    # migrate individual aggregates to prefixes
    for instance in Aggregate.objects.all():
        if Prefix.objects.filter(
            network=instance.network,
            prefix_length=instance.prefix_length,
            vrf__isnull=True,
        ).exists():
            prefix = Prefix.objects.get(network=instance.network, prefix_length=instance.prefix_length)
            mismatches.update(_migrate_aggregate_to_existing_prefix(instance, prefix))

        else:
            prefix = Prefix.objects.create(
                id=instance.id,
                broadcast=instance.broadcast,
                date_allocated=_convert_date_to_datetime(instance.date_added),
                description=instance.description,
                network=instance.network,
                prefix_length=instance.prefix_length,
                rir=instance.rir,
                status=prefix_default_status,
                tenant=instance.tenant,
                type=PrefixTypeChoices.TYPE_CONTAINER,
            )

        # use `migrated_to_prefix` ForeignKey reference on Aggregate to assist with app migrations
        instance.migrated_to_prefix = prefix
        instance.save()

        # migrate all notes assigned to this aggregate to the new prefix
        _migrate_aggregate_notes_to_prefix(apps, instance, aggregate_ct, prefix_ct)

        # migrate all object changes related to this aggregate to the new prefix
        _migrate_aggregate_object_changes_to_prefix(apps, instance, aggregate_ct, prefix_ct)

        # migrate all tags related to this aggregate to the new prefix
        _migrate_aggregate_tags_to_prefix(apps, instance, aggregate_ct, prefix_ct)

        # migrate custom fields on this aggregate to the new prefix
        mismatches.update(_migrate_aggregate_custom_fields_to_prefix(instance))

        # migrate all relationship associations related to this aggregate to the new prefix
        _migrate_aggregate_relationships_to_prefix(apps, instance, aggregate_ct, prefix_ct)

        # make tag manager available in migration for nautobot.core.models.utils.serialize_object
        # https://github.com/jazzband/django-taggit/issues/101
        # https://github.com/jazzband/django-taggit/issues/454
        prefix.tags = TagsManager(
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

        error_message = (
            "\n",
            f"Unable to migrate all fields from Aggregate {instance.network}/{instance.prefix_length} to Prefix due to an existing Prefix.",
            f"Some of the following data may have to be migrated manually: {mismatches}",
        )
        if mismatches:
            print(" ".join(error_message), flush=True)


class Migration(migrations.Migration):
    dependencies = [
        ("ipam", "0021_prefix_add_rir_and_date_allocated"),
        ("extras", "0039_objectchange__add_change_context"),
    ]

    operations = [
        migrations.RunPython(
            code=migrate_aggregate_to_prefix,
            reverse_code=migrations.operations.special.RunPython.noop,
        ),
    ]
