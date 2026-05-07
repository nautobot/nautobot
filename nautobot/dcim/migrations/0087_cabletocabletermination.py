# Cable changes + CableToCableTermination join model.
import uuid

from django.db import migrations, models
import django.db.models.deletion

# The CheckConstraint expression below is built programmatically because the 9-clause OR is too
# verbose to maintain by hand. It mirrors `_exactly_one_termination_q` in nautobot/dcim/models/cables.py.
_TERMINATION_FK_FIELDS = (
    "circuit_termination",
    "console_port",
    "console_server_port",
    "front_port",
    "interface",
    "power_feed",
    "power_outlet",
    "power_port",
    "rear_port",
)


def _exactly_one_termination_check():
    expr = models.Q()
    for field in _TERMINATION_FK_FIELDS:
        clause = models.Q(**{f"{field}__isnull": False})
        for other in _TERMINATION_FK_FIELDS:
            if other != field:
                clause &= models.Q(**{f"{other}__isnull": True})
        expr |= clause
    return expr


class Migration(migrations.Migration):
    dependencies = [
        ("circuits", "0022_circuittermination_cloud_network"),
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
                ("connector", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("position", models.PositiveSmallIntegerField(blank=True, null=True)),
                (
                    "cable",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="terminations", to="dcim.cable"
                    ),
                ),
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
                    "circuit_termination",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cable_termination",
                        to="circuits.circuittermination",
                    ),
                ),
                (
                    "console_port",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cable_termination",
                        to="dcim.consoleport",
                    ),
                ),
                (
                    "console_server_port",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cable_termination",
                        to="dcim.consoleserverport",
                    ),
                ),
                (
                    "front_port",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cable_termination",
                        to="dcim.frontport",
                    ),
                ),
                (
                    "interface",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cable_termination",
                        to="dcim.interface",
                    ),
                ),
                (
                    "power_feed",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cable_termination",
                        to="dcim.powerfeed",
                    ),
                ),
                (
                    "power_outlet",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cable_termination",
                        to="dcim.poweroutlet",
                    ),
                ),
                (
                    "power_port",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cable_termination",
                        to="dcim.powerport",
                    ),
                ),
                (
                    "rear_port",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cable_termination",
                        to="dcim.rearport",
                    ),
                ),
            ],
            options={
                "ordering": ["cable", "cable_end", "connector", "position"],
            },
        ),
        migrations.AddConstraint(
            model_name="cabletocabletermination",
            constraint=models.UniqueConstraint(
                fields=("cable", "cable_end"),
                condition=models.Q(("connector__isnull", True)),
                name="dcim_cabletocabletermination_unique_nonbreakout_lane",
            ),
        ),
        migrations.AddConstraint(
            model_name="cabletocabletermination",
            constraint=models.UniqueConstraint(
                fields=("cable", "cable_end", "connector", "position"),
                condition=models.Q(("connector__isnull", False)),
                name="dcim_cabletocabletermination_unique_breakout_lane",
            ),
        ),
        migrations.AddConstraint(
            model_name="cabletocabletermination",
            constraint=models.CheckConstraint(
                check=_exactly_one_termination_check(),
                name="dcim_cabletocabletermination_exactly_one_termination",
            ),
        ),
        # Typed many-to-many accessors on Cable that resolve through CableToCableTermination.
        migrations.AddField(
            model_name="cable",
            name="circuit_terminations",
            field=models.ManyToManyField(
                related_name="+",
                through="dcim.CableToCableTermination",
                through_fields=("cable", "circuit_termination"),
                to="circuits.circuittermination",
            ),
        ),
        migrations.AddField(
            model_name="cable",
            name="console_ports",
            field=models.ManyToManyField(
                related_name="+",
                through="dcim.CableToCableTermination",
                through_fields=("cable", "console_port"),
                to="dcim.consoleport",
            ),
        ),
        migrations.AddField(
            model_name="cable",
            name="console_server_ports",
            field=models.ManyToManyField(
                related_name="+",
                through="dcim.CableToCableTermination",
                through_fields=("cable", "console_server_port"),
                to="dcim.consoleserverport",
            ),
        ),
        migrations.AddField(
            model_name="cable",
            name="front_ports",
            field=models.ManyToManyField(
                related_name="+",
                through="dcim.CableToCableTermination",
                through_fields=("cable", "front_port"),
                to="dcim.frontport",
            ),
        ),
        migrations.AddField(
            model_name="cable",
            name="interfaces",
            field=models.ManyToManyField(
                related_name="+",
                through="dcim.CableToCableTermination",
                through_fields=("cable", "interface"),
                to="dcim.interface",
            ),
        ),
        migrations.AddField(
            model_name="cable",
            name="power_feeds",
            field=models.ManyToManyField(
                related_name="+",
                through="dcim.CableToCableTermination",
                through_fields=("cable", "power_feed"),
                to="dcim.powerfeed",
            ),
        ),
        migrations.AddField(
            model_name="cable",
            name="power_outlets",
            field=models.ManyToManyField(
                related_name="+",
                through="dcim.CableToCableTermination",
                through_fields=("cable", "power_outlet"),
                to="dcim.poweroutlet",
            ),
        ),
        migrations.AddField(
            model_name="cable",
            name="power_ports",
            field=models.ManyToManyField(
                related_name="+",
                through="dcim.CableToCableTermination",
                through_fields=("cable", "power_port"),
                to="dcim.powerport",
            ),
        ),
        migrations.AddField(
            model_name="cable",
            name="rear_ports",
            field=models.ManyToManyField(
                related_name="+",
                through="dcim.CableToCableTermination",
                through_fields=("cable", "rear_port"),
                to="dcim.rearport",
            ),
        ),
    ]
