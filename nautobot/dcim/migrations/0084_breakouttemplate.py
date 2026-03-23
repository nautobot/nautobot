# Create BreakoutTemplate model.
# CableTerminationEndpoint, Cable.breakout_template FK, and Cable ordering changes are in commit 3.

import uuid

import django.core.serializers.json
from django.db import migrations, models

import nautobot.core.models.fields
import nautobot.extras.models.mixins


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0083_alter_controllermanageddevicegroup_radio_profiles_and_more"),
        ("extras", "0138_job_console_log_default_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="BreakoutTemplate",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                (
                    "_custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder),
                ),
                ("name", models.CharField(max_length=255, unique=True)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("a_connectors", models.PositiveSmallIntegerField()),
                ("a_positions", models.PositiveSmallIntegerField()),
                ("b_connectors", models.PositiveSmallIntegerField()),
                ("b_positions", models.PositiveSmallIntegerField()),
                ("mapping", models.JSONField()),
                ("is_shuffle", models.BooleanField(default=False)),
                ("strands_per_lane", models.PositiveSmallIntegerField(default=1)),
                ("polarity_method", models.CharField(blank=True, max_length=50)),
                ("tags", nautobot.core.models.fields.TagsField(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={
                "ordering": ["name"],
            },
            bases=(
                nautobot.extras.models.mixins.DataComplianceModelMixin,
                nautobot.extras.models.mixins.DynamicGroupMixin,
                nautobot.extras.models.mixins.NotesMixin,
                models.Model,
            ),
        ),
    ]
