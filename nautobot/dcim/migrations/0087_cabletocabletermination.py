# Cable changes + CableToCableTermination join model.
import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("dcim", "0086_populate_default_cable_types"),
    ]
    operations = [
        migrations.AlterModelOptions(name="cable", options={"ordering": ["label", "pk"]}),
        migrations.AlterUniqueTogether(name="cable", unique_together=set()),
        migrations.AddField(
            model_name="cable",
            name="cable_type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="cables",
                to="dcim.cabletype",
            ),
        ),
        migrations.CreateModel(
            name="CableToCableTermination",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True
                    ),
                ),
                ("cable_end", models.CharField(max_length=1)),
                ("termination_id", models.UUIDField()),
                ("connector", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("position", models.PositiveSmallIntegerField(blank=True, null=True)),
                (
                    "_termination_device",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="dcim.device",
                    ),
                ),
                (
                    "cable",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="terminations", to="dcim.cable"
                    ),
                ),
                (
                    "termination_type",
                    models.ForeignKey(
                        limit_choices_to=models.Q(
                            models.Q(
                                models.Q(("app_label", "circuits"), ("model__in", ("circuittermination",))),
                                models.Q(
                                    ("app_label", "dcim"),
                                    (
                                        "model__in",
                                        (
                                            "consoleport",
                                            "consoleserverport",
                                            "frontport",
                                            "interface",
                                            "powerfeed",
                                            "poweroutlet",
                                            "powerport",
                                            "rearport",
                                        ),
                                    ),
                                ),
                                _connector="OR",
                            )
                        ),
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="contenttypes.contenttype",
                    ),
                ),
            ],
            options={
                "ordering": ["cable", "cable_end", "connector", "position"],
                "unique_together": {("termination_type", "termination_id")},
            },
        ),
    ]
