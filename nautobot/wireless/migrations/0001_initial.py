# Generated by Django 4.2.16 on 2024-11-05 13:48

import uuid

import django.core.serializers.json
from django.db import migrations, models
import django.db.models.deletion

import nautobot.core.models.fields
import nautobot.extras.models.mixins


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("extras", "0119_remove_task_queues_from_job_and_queue_from_scheduled_job"),
        ("dcim", "0065_controller_capabilities_and_more"),
        ("ipam", "0050_vlangroup_range"),
        ("tenancy", "0009_update_all_charfields_max_length_to_255"),
    ]

    operations = [
        migrations.CreateModel(
            name="WirelessNetwork",
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
                ("ssid", models.CharField(max_length=255)),
                ("mode", models.CharField(max_length=255)),
                ("enabled", models.BooleanField(default=True)),
                ("authentication", models.CharField(max_length=255)),
                ("hidden", models.BooleanField(default=False)),
                (
                    "secrets_group",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="wireless_networks",
                        to="extras.secretsgroup",
                    ),
                ),
                ("tags", nautobot.core.models.fields.TagsField(through="extras.TaggedItem", to="extras.Tag")),
                (
                    "tenant",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="wireless_networks",
                        to="tenancy.tenant",
                    ),
                ),
            ],
            options={
                "ordering": ["name"],
            },
            bases=(
                nautobot.extras.models.mixins.DynamicGroupMixin,
                nautobot.extras.models.mixins.NotesMixin,
                models.Model,
            ),
        ),
        migrations.CreateModel(
            name="SupportedDataRate",
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
                ("standard", models.CharField(max_length=255)),
                ("rate", models.PositiveIntegerField()),
                ("mcs_index", models.IntegerField(blank=True, null=True)),
                ("tags", nautobot.core.models.fields.TagsField(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={
                "ordering": ["standard", "rate"],
                "unique_together": {("standard", "rate")},
            },
            bases=(
                nautobot.extras.models.mixins.DynamicGroupMixin,
                nautobot.extras.models.mixins.NotesMixin,
                models.Model,
            ),
        ),
        migrations.CreateModel(
            name="RadioProfile",
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
                ("frequency", models.CharField(blank=True, max_length=255)),
                ("tx_power_min", models.IntegerField(blank=True, null=True)),
                ("tx_power_max", models.IntegerField(blank=True, null=True)),
                (
                    "channel_width",
                    nautobot.core.models.fields.JSONArrayField(base_field=models.IntegerField(), blank=True, null=True),
                ),
                (
                    "allowed_channel_list",
                    nautobot.core.models.fields.JSONArrayField(base_field=models.IntegerField(), blank=True, null=True),
                ),
                ("regulatory_domain", models.CharField(max_length=255)),
                ("rx_power_min", models.IntegerField(blank=True, null=True)),
                (
                    "supported_data_rates",
                    models.ManyToManyField(blank=True, related_name="radio_profiles", to="wireless.supporteddatarate"),
                ),
                ("tags", nautobot.core.models.fields.TagsField(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={
                "ordering": ["name"],
            },
            bases=(
                nautobot.extras.models.mixins.DynamicGroupMixin,
                nautobot.extras.models.mixins.NotesMixin,
                models.Model,
            ),
        ),
        migrations.CreateModel(
            name="ControllerManagedDeviceGroupWirelessNetworkAssignment",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True
                    ),
                ),
                (
                    "controller_managed_device_group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="wireless_network_assignments",
                        to="dcim.controllermanageddevicegroup",
                    ),
                ),
                (
                    "vlan",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="controller_managed_device_group_wireless_network_assignments",
                        to="ipam.vlan",
                    ),
                ),
                (
                    "wireless_network",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="controller_managed_device_group_assignments",
                        to="wireless.wirelessnetwork",
                    ),
                ),
            ],
            options={
                "ordering": ["controller_managed_device_group", "wireless_network"],
                "unique_together": {("controller_managed_device_group", "wireless_network")},
            },
        ),
        migrations.CreateModel(
            name="ControllerManagedDeviceGroupRadioProfileAssignment",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True
                    ),
                ),
                (
                    "controller_managed_device_group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="radio_profile_assignments",
                        to="dcim.controllermanageddevicegroup",
                    ),
                ),
                (
                    "radio_profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="controller_managed_device_group_assignments",
                        to="wireless.radioprofile",
                    ),
                ),
            ],
            options={
                "ordering": ["controller_managed_device_group", "radio_profile"],
                "unique_together": {("controller_managed_device_group", "radio_profile")},
            },
        ),
    ]
