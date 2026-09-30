"""System job that seeds demo data for the Provenance tab."""

import uuid
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from nautobot.extras.jobs import BooleanVar, Job
from nautobot.dcim.models import Device, DeviceType, Location, LocationType, Manufacturer
from nautobot.extras.choices import MetadataTypeDataTypeChoices, ObjectChangeEventContextChoices
from nautobot.extras.context_managers import web_request_context
from nautobot.extras.models import Contact, MetadataType, ObjectChange, ObjectMetadata, Role, Status, Tag, Team

name = "System Jobs"  # pylint: disable=invalid-name

DEVICE_NAMES = ("prov-demo-leaf-01", "prov-demo-leaf-02", "prov-demo-leaf-03")
CHANGE_DETAIL = "provenance-seed"
DEMO_LABEL = "Provenance demo"
METADATA_TYPE_NAME = f"{DEMO_LABEL} data owner"
TEAM_NAME = f"{DEMO_LABEL} network engineering"
CONTACT_NAME = f"{DEMO_LABEL} facilities"
TAG_NAMES = ("prov-demo", "prov-demo-maintenance")

WEB = ObjectChangeEventContextChoices.CONTEXT_WEB
JOB = ObjectChangeEventContextChoices.CONTEXT_JOB
ORM = ObjectChangeEventContextChoices.CONTEXT_ORM
# Context details mirror what Nautobot records: the resolved view name for UI and REST API requests, the job
# class path for jobs, and a free-form tag for ORM/shell changes.
UI_DETAIL = "dcim:device_edit"
API_DETAIL = "dcim-api:device-detail"
JOB_DETAIL = "nautobot.core.jobs.provenance_demo.SeedProvenanceDemo"
SHELL_DETAIL = "nbshell"

# (days ago, user name, change context, context detail, attribute changes) applied to every demo device in
# order. Statuses and tags are resolved by name at run time.
SCRIPT = (
    (30, "provisioning-bot", JOB, JOB_DETAIL, {"status": "Planned"}),
    (28, "jsmith", WEB, UI_DETAIL, {"serial": "SN-{index:02d}-A"}),
    (26, "cmdb-sync", WEB, API_DETAIL, {"asset_tag": "ASSET-{index:02d}"}),
    (24, "jsmith", WEB, UI_DETAIL, {"status": "Staged", "tags": ["prov-demo"]}),
    (19, "provisioning-bot", JOB, JOB_DETAIL, {"local_config_context_data": {"ntp": {"servers": ["10.0.0.1"]}}}),
    (15, "cmdb-sync", WEB, API_DETAIL, {"status": "Active", "comments": "Turned up during the spring build."}),
    (11, "netops-oncall", ORM, SHELL_DETAIL, {"comments": "Turned up during the spring build. Uplink optic to spine-02 replaced."}),
    (8, "provisioning-bot", JOB, JOB_DETAIL, {"local_config_context_data": {"ntp": {"servers": ["10.0.0.1", "10.0.0.2"]}}}),
    (5, "rma-desk", WEB, UI_DETAIL, {"status": "Offline", "tags": ["prov-demo", "prov-demo-maintenance"]}),
    (3, "rma-desk", WEB, API_DETAIL, {"serial": "SN-{index:02d}-B"}),
    (1, "cmdb-sync", WEB, API_DETAIL, {"status": "Active", "tags": ["prov-demo"]}),
)


class SeedProvenanceDemo(Job):
    """Create three demo devices, each with a month of logged changes, so the Provenance tab has history to show."""

    flush = BooleanVar(description="Remove everything this job created instead of creating it.", default=False)

    class Meta:
        """Job metadata."""

        name = "Seed Provenance demo data"
        description = (
            "Creates three demo devices with several backdated, logged changes each and an owner set through "
            "Object Metadata. Safe to run again. Check Flush to remove everything the job created."
        )
        has_sensitive_variables = False

    def run(self, flush=False):  # pylint: disable=arguments-differ
        """Seed or flush the demo data."""
        if flush:
            self._flush()
            return "Demo data removed."
        if Device.objects.filter(name__in=DEVICE_NAMES).exists():
            self.logger.info("Demo devices already exist; nothing to do. Check Flush to remove them first.")
            return "Demo data already present."
        self._seed()
        return f"Created {len(DEVICE_NAMES)} demo devices with {len(SCRIPT)} logged changes each."

    # -- seeding -------------------------------------------------------------------------------------------------

    def _logged(self, detail=CHANGE_DETAIL, change_id=None, context=JOB):
        """A change-logging context with its own change id, so each step becomes its own change record."""
        return web_request_context(
            self.user,
            context_detail=detail,
            change_id=change_id or uuid.uuid4(),
            context=context,
        )

    def _seed(self):
        device_ct = ContentType.objects.get_for_model(Device)
        with self._logged():
            location_type, _ = LocationType.objects.get_or_create(name=f"{DEMO_LABEL} site")
            location_type.content_types.add(device_ct)
            location, _ = Location.objects.get_or_create(
                name=f"{DEMO_LABEL} DC1",
                location_type=location_type,
                defaults={"status": Status.objects.get_for_model(Location).get(name="Active")},
            )
            manufacturer, _ = Manufacturer.objects.get_or_create(name=DEMO_LABEL)
            device_type, _ = DeviceType.objects.get_or_create(manufacturer=manufacturer, model=f"{DEMO_LABEL} leaf")
            role, _ = Role.objects.get_or_create(name=f"{DEMO_LABEL} leaf role")
            role.content_types.add(device_ct)
            for tag_name in TAG_NAMES:
                tag, _ = Tag.objects.get_or_create(name=tag_name)
                tag.content_types.add(device_ct)

        statuses = {status.name: status for status in Status.objects.get_for_model(Device)}
        tags = {tag.name: tag for tag in Tag.objects.filter(name__in=TAG_NAMES)}

        for index, device_name in enumerate(DEVICE_NAMES, start=1):
            days_ago, user_name, context, detail, first_changes = SCRIPT[0]
            change_id = uuid.uuid4()
            with self._logged(detail=detail, change_id=change_id, context=context):
                device = Device(
                    name=device_name,
                    device_type=device_type,
                    role=role,
                    location=location,
                    status=statuses[first_changes["status"]],
                )
                device.validated_save()
            self._backdate(change_id, device, days_ago, index, user_name)

            for days_ago, user_name, context, detail, changes in SCRIPT[1:]:
                change_id = uuid.uuid4()
                with self._logged(detail=detail, change_id=change_id, context=context):
                    self._apply(device, changes, index, statuses, tags)
                self._backdate(change_id, device, days_ago, index, user_name)
            self.logger.info("Seeded %s with %d logged changes.", device_name, len(SCRIPT), extra={"object": device})

        self._seed_owner()

    @staticmethod
    def _apply(device, changes, index, statuses, tags):
        for attribute, value in changes.items():
            if attribute == "status":
                device.status = statuses[value]
            elif attribute == "tags":
                device.tags.set([tags[tag_name] for tag_name in value])
            elif isinstance(value, str):
                setattr(device, attribute, value.format(index=index))
            else:
                setattr(device, attribute, value)
        device.validated_save()

    @staticmethod
    def _backdate(change_id, device, days_ago, index, user_name):
        """Move the change records written under ``change_id`` into the past and stamp a demo user name on them.

        Each device is offset by a few hours so the three devices do not share identical timestamps.
        """
        ObjectChange.objects.filter(changed_object_id=device.pk, request_id=change_id).update(
            time=timezone.now() - timedelta(days=days_ago, hours=5 * index, minutes=7 * index), user_name=user_name
        )

    def _seed_owner(self):
        device_ct = ContentType.objects.get_for_model(Device)
        with self._logged():
            metadata_type, _ = MetadataType.objects.get_or_create(
                name=METADATA_TYPE_NAME, defaults={"data_type": MetadataTypeDataTypeChoices.TYPE_CONTACT_TEAM}
            )
            metadata_type.content_types.add(device_ct)
            team, _ = Team.objects.get_or_create(name=TEAM_NAME)
            contact, _ = Contact.objects.get_or_create(name=CONTACT_NAME)
            leaf_01 = Device.objects.get(name=DEVICE_NAMES[0])
            leaf_02 = Device.objects.get(name=DEVICE_NAMES[1])
            ObjectMetadata.objects.get_or_create(
                metadata_type=metadata_type,
                assigned_object_type=device_ct,
                assigned_object_id=leaf_01.pk,
                defaults={"team": team, "scoped_fields": ["status", "role"]},
            )
            ObjectMetadata.objects.get_or_create(
                metadata_type=metadata_type,
                assigned_object_type=device_ct,
                assigned_object_id=leaf_02.pk,
                defaults={"contact": contact, "scoped_fields": ["location"]},
            )
        self.logger.info("Named %s as owner of status and role on %s.", TEAM_NAME, DEVICE_NAMES[0])

    # -- flushing ------------------------------------------------------------------------------------------------

    def _flush(self):
        with self._logged("provenance-seed-flush"):
            deleted, _ = Device.objects.filter(name__in=DEVICE_NAMES).delete()
            self.logger.info("Deleted %d demo device rows (including related objects).", deleted)
            MetadataType.objects.filter(name=METADATA_TYPE_NAME).delete()
            Team.objects.filter(name=TEAM_NAME).delete()
            Contact.objects.filter(name=CONTACT_NAME).delete()
            Tag.objects.filter(name__in=TAG_NAMES).delete()
            DeviceType.objects.filter(manufacturer__name=DEMO_LABEL).delete()
            Manufacturer.objects.filter(name=DEMO_LABEL).delete()
            Role.objects.filter(name=f"{DEMO_LABEL} leaf role").delete()
            Location.objects.filter(name=f"{DEMO_LABEL} DC1").delete()
            LocationType.objects.filter(name=f"{DEMO_LABEL} site").delete()

