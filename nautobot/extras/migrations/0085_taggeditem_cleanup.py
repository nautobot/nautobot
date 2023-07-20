from django.db import migrations, models


def cleanup_taggeditem_duplicates(apps, schema_editor):
    TaggedItem = apps.get_model("extras", "TaggedItem")

    # Get the set of distinct values for TaggedItems
    taggeditem_values = TaggedItem.objects.values("content_type", "object_id", "tag")
    # Discard any existing ordering, just to be safe
    taggeditem_values = taggeditem_values.order_by()
    # Count the number of duplicates for each value
    taggeditem_values = taggeditem_values.annotate(count_id=models.Count("id"))

    # Filter to only those that actually have duplicates (i.e. more than one record)
    duplicate_taggeditem_values = taggeditem_values.filter(count_id__gt=1)

    deleted_count = 0
    for duplicate in duplicate_taggeditem_values:
        # Delete all but the "first" in each duplicate set.
        # We can't use models.Min("id") to deterministically pick which one to keep because id is a UUID and psycopg2
        # doesn't implement a min(uuid) function.
        # We also can't just slice the queryset before deleting it (Django doesn't allow it).
        to_delete = TaggedItem.objects.filter(
            content_type=duplicate["content_type"], object_id=duplicate["object_id"], tag=duplicate["tag"]
        )
        to_keep = to_delete.first()
        to_delete = to_delete.exclude(id=to_keep.id)

        count, _ = to_delete.delete()
        deleted_count += count

    if deleted_count:
        print(f"    Deleted {deleted_count} redundant TaggedItem records")


class Migration(migrations.Migration):
    dependencies = [
        ("extras", "0084_rename_computed_field_slug_to_key"),
    ]

    operations = [
        migrations.RunPython(cleanup_taggeditem_duplicates, migrations.RunPython.noop),
    ]
