# Create CableBreakoutType model.

import uuid

import django.core.serializers.json
import django.core.validators
from django.db import migrations, models

import nautobot.core.models.fields
import nautobot.extras.models.mixins


class Migration(migrations.Migration):
    dependencies = [
        ("dcim", "0084_add_module_type_image_support"),
        ("extras", "0138_job_console_log_default_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="CableBreakoutType",
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
                (
                    "a_connectors",
                    models.PositiveSmallIntegerField(
                        default=1, validators=[django.core.validators.MaxValueValidator(16)]
                    ),
                ),
                (
                    "a_positions",
                    models.PositiveSmallIntegerField(
                        default=1, validators=[django.core.validators.MaxValueValidator(16)]
                    ),
                ),
                (
                    "b_connectors",
                    models.PositiveSmallIntegerField(
                        default=1, validators=[django.core.validators.MaxValueValidator(16)]
                    ),
                ),
                (
                    "b_positions",
                    models.PositiveSmallIntegerField(
                        default=1, validators=[django.core.validators.MaxValueValidator(16)]
                    ),
                ),
                ("mapping", models.JSONField()),
                ("is_shuffle", models.BooleanField(default=False)),
                (
                    "strands_per_lane",
                    models.PositiveSmallIntegerField(
                        default=1, validators=[django.core.validators.MinValueValidator(1)]
                    ),
                ),
                ("polarity_method", models.CharField(blank=True, default="", max_length=50)),
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
