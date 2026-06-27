# Cable changes + CableToCableTermination join model.
import uuid

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion

# The CheckConstraint expression below is built programmatically because the 10-clause OR is too
# verbose to maintain by hand. It mirrors `_at_most_one_termination_q` in nautobot/dcim/models/cables.py.
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


def _at_most_one_termination_check():
    expr = models.Q(**{f"{field}__isnull": True for field in _TERMINATION_FK_FIELDS})
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
        ("dcim", "0087_populate_default_cable_types"),
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
                (
                    "connector",
                    models.PositiveSmallIntegerField(
                        default=1,
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(16),  # CABLE_BREAKOUT_MAX_CONNECTORS
                        ],
                    ),
                ),
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
                "ordering": ["cable", "cable_end", "connector"],
            },
        ),
        migrations.AddConstraint(
            model_name="cabletocabletermination",
            constraint=models.UniqueConstraint(
                fields=("cable", "cable_end", "connector"),
                name="dcim_cabletocabletermination_unique_connector",
            ),
        ),
        migrations.AddConstraint(
            model_name="cabletocabletermination",
            constraint=models.CheckConstraint(
                condition=_at_most_one_termination_check(),
                name="dcim_cabletocabletermination_at_most_one_termination",
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
        # Breakout child-interface position: which position on the parent (trunk) interface's
        # breakout connector a child interface maps to.
        migrations.AddField(
            model_name="interface",
            name="breakout_position",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(256),  # CABLE_BREAKOUT_MAX_LANES
                ],
                help_text=(
                    "For a child interface of a breakout-cable trunk, the position on the parent "
                    "interface's trunk connector that this child interface maps to."
                ),
            ),
        ),
        migrations.AddConstraint(
            model_name="interface",
            constraint=models.UniqueConstraint(
                fields=("parent_interface", "breakout_position"),
                name="dcim_interface_unique_parent_breakout_position",
            ),
        ),
    ]
