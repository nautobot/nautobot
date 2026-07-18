"""Object Lock schema and seed data.

Creates the ObjectLock claim model, the ObjectLockGeneration token, and the ObjectLockBypassAudit
record, and seeds the singleton generation token. The Object Lock Sweep ships as an enabled system
Job; operators schedule it (e.g. daily) to purge expired/orphaned lock records — it is not
auto-scheduled, matching every other Nautobot system Job.
"""

import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_generation_token(apps, schema_editor):
    """Seed the singleton ObjectLockGeneration row so the first token bump never races on insert."""
    apps.get_model("extras", "ObjectLockGeneration").objects.get_or_create(pk=1, defaults={"token": 0})


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("extras", "0142_remove_scheduledjob_approval_required"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ObjectLock",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                ("object_id", models.UUIDField(db_index=True)),
                ("prevent_delete", models.BooleanField(default=True)),
                ("prevent_update", models.BooleanField(default=False)),
                ("locked_fields", models.JSONField(blank=True, null=True)),
                ("reason", models.TextField(blank=True)),
                ("source_context", models.CharField(default="orm", max_length=50)),
                ("source_detail", models.CharField(blank=True, max_length=255)),
                ("source_key", models.CharField(max_length=255)),
                ("expires", models.DateTimeField(blank=True, null=True)),
                (
                    "content_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="object_locks",
                        to="contenttypes.contenttype",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="object_locks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["content_type", "object_id", "source_key"],
                "verbose_name": "Object Lock",
                "verbose_name_plural": "Object Locks",
                "permissions": [
                    ("bypass_objectlock", "Can bypass an Object Lock to modify a locked object"),
                    ("force_release_objectlock", "Can release an Object Lock created by a different source"),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("content_type", "object_id", "source_key"), name="extras_objectlock_unique_source"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="ObjectLockGeneration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("token", models.BigIntegerField(default=0)),
            ],
            options={
                "verbose_name": "Object Lock generation token",
            },
        ),
        migrations.CreateModel(
            name="ObjectLockBypassAudit",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True
                    ),
                ),
                ("time", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("object_id", models.UUIDField(db_index=True)),
                ("change_id", models.UUIDField(blank=True, null=True)),
                ("suspended_source_keys", models.JSONField(default=list)),
                ("suspended_fields", models.JSONField(default=list)),
                ("suspended_other_source", models.BooleanField(default=False)),
                (
                    "content_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="object_lock_bypass_audits",
                        to="contenttypes.contenttype",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="object_lock_bypass_audits",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Object Lock bypass audit",
                "verbose_name_plural": "Object Lock bypass audits",
                "ordering": ["-time"],
            },
        ),
        migrations.RunPython(seed_generation_token, migrations.RunPython.noop),
    ]
