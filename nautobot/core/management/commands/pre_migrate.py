# TODO(jathan): This file MUST NOT be merged into Nautobot v2 (next).

import argparse
import json

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import models
from django.db.models.fields.json import KeyTransform

from nautobot.circuits.models import Circuit
from nautobot.dcim.models import (
    CablePath,
    Device,
    DeviceRedundancyGroup,
    DeviceRole,
    DeviceType,
    FrontPortTemplate,
    InventoryItem,
    Location,
    PowerOutletTemplate,
    PowerPanel,
    PowerPort,
    PowerPortTemplate,
    Rack,
    RackGroup,
    RackRole,
    RearPort,
    RearPortTemplate,
    Region,
    Site,
    VirtualChassis,
)
from nautobot.extras.models import (
    ConfigContext,
    ConfigContextSchema,
    CustomField,
    CustomFieldChoice,
    ExportTemplate,
    GitRepository,
    Job,
    JobResult,
    Relationship,
    ScheduledJob,
    Secret,
    SecretsGroup,
    SecretsGroupAssociation,
    Status,
    TaggedItem,
)
from nautobot.ipam.models import Aggregate, IPAddress, Prefix, RIR, Role, Service, VLAN, VRF
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.users.models import ObjectPermission, User
from nautobot.virtualization.models import Cluster, VirtualMachine

HELP_TEXT = """
Performs pre-migration validation checks for Nautobot 2.0.

If the Nautobot 1.x instance cannot be upgraded, this command will exit uncleanly.

Also emits informational messages to help identify permissions that may need to be manually updated after upgrading to Nautobot 2.0.
"""


def check_virtualchassis_uniqueness():
    """
    Check for uniqueness enforcement changes for VirtualChassis.

    - Make `name` unique, reject migration if duplicate (don't want to rename VCs)

    See: https://github.com/nautobot/nautobot/issues/3846
    """
    vc_dupes = VirtualChassis.objects.values("name").annotate(count=models.Count("id")).filter(count__gt=1)

    if vc_dupes.exists():
        raise ValidationError(
            f"You cannot migrate VirtualChassis objects with non-unique names:\n - {list(vc_dupes)}\n"
        )


def check_exporttemplate_uniqueness():
    """
    Check for uniqueness enforcement changes for ExportTemplate.

    - Move to `unique_together` on just `content_type` and `name`, reject migration if duplicate.

    See: https://github.com/nautobot/nautobot/issues/3848
    """
    et_dupes = (
        ExportTemplate.objects.values("content_type", "name").annotate(count=models.Count("id")).filter(count__gt=1)
    )

    if et_dupes.exists():
        raise ValidationError(
            f"You cannot migrate ExportTemplate objects with non-unique content_type, name pairs:\n - {list(et_dupes)}\n"
        )


def check_configcontext_uniqueness():
    """
    Check for uniqueness enforcement changes for ConfigContext and ConfigContextSchema.

    - Move to `name` unique, reject migration if duplicate

    See: https://github.com/nautobot/nautobot/issues/3849
    """
    cc_dupes = ConfigContext.objects.values("name").annotate(count=models.Count("id")).filter(count__gt=1)
    ccs_dupes = ConfigContextSchema.objects.values("name").annotate(count=models.Count("id")).filter(count__gt=1)

    if any(
        [
            cc_dupes.exists(),
            ccs_dupes.exists(),
        ]
    ):
        raise ValidationError(
            "You cannot migrate ConfigContext or ConfigContextSchema objects that have non-unique names:\n"
            f"- ConfigContext: {list(cc_dupes)}\n"
            f"- ConfigContextSchema: {list(ccs_dupes)}\n"
        )


def check_interface_ipaddress_vrf_uniqueness(command):
    """
    Check for uniqueness enforcement changes for Interface and VMInterface IPAddress assignments.

    - All IP Addresses assigned to a specific Interface or VMInterface must share the same VRF or have no VRF.
    """

    failed = False

    command.stdout.write(command.style.WARNING(">>> Running interface/vminterface vrf uniqueness checks..."))

    for ip_address_assignment in (
        IPAddress.objects.filter(assigned_object_id__isnull=False, assigned_object_type_id__isnull=False)
        .values("assigned_object_type", "assigned_object_id")
        .annotate(
            vrf_count=models.Count("vrf_id", distinct=True),
            vrf_null_count=models.Count("pk", filter=models.Q(vrf_id__isnull=True)),
        )
        .order_by()
    ):
        has_null_vrf = 1 if ip_address_assignment["vrf_null_count"] > 0 else 0
        if ip_address_assignment["vrf_count"] + has_null_vrf > 1:
            try:
                assigned_object_type = ContentType.objects.get_for_id(
                    ip_address_assignment["assigned_object_type"]
                ).model_class()
            except ContentType.DoesNotExist:
                continue

            if assigned_object_type is None:
                continue  # ContentType.model_class() can return None if an App was removed from the installed_plugins list

            try:
                assigned_object = assigned_object_type.objects.get(pk=ip_address_assignment["assigned_object_id"])
            except assigned_object_type.DoesNotExist:
                continue

            failed = True
            assigned_object_label = f"{assigned_object} ({getattr(assigned_object, 'parent', assigned_object.id)})"
            command.stdout.write(
                command.style.WARNING(
                    f"{assigned_object_type._meta.label} {assigned_object_label} "
                    "is associated to IP Addresses with different VRFs."
                )
            )

    if failed:
        raise ValidationError(
            "You cannot migrate Interfaces or VMInterfaces associated to multiple IP Addresses with different VRFs."
        )


def check_permissions_constraints(command):
    """
    Check for permission constraints that are referencing an object or field
    that will be migrated to a different model/field/value in 2.0 migrations.

    Objects that will be replaced in 2.0 are:
    - dcim.DeviceRole
    - dcim.RackRole
    - dcim.Region
    - dcim.Site
    - ipam.Aggregate
    - ipam.Role

    Objects that will possibly have fields migrated to a different value in 2.0 are:
    - ipam.IPAddress
    - ipam.Prefix
    - ipam.Service
    - extras.CustomField
    - extras.GitRepository
    - extras.Job
    - extras.ObjectPermission
    - extras.ScheduledJob
    - extras.TaggedItem

    Objects that had fields renamed or removed in 2.0 are:
    - circuits.Circuit
    - ContentType
    - dcim.CablePath
    - dcim.Device
    - dcim.DeviceRedundancyGroup
    - dcim.DeviceType
    - dcim.FrontPortTemplate
    - dcim.InventoryItem
    - dcim.Location
    - dcim.PowerOutletTemplate
    - dcim.PowerPanel
    - dcim.PowerPort
    - dcim.PowerPortTemplate
    - dcim.Rack
    - dcim.RackGroup
    - dcim.RearPort
    - dcim.RearPortTemplate
    - extras.ComputedField
    - extras.ConfigContext
    - extras.ConfigContextSchema
    - extras.CustomField
    - extras.CustomFieldChoice
    - extras.Job
    - extras.JobResult
    - extras.Relationship
    - extras.Secret
    - extras.SecretsGroup
    - extras.SecretsGroupAssociation
    - extras.Status
    - ipam.IPAddress
    - ipam.Prefix
    - ipam.RIR
    - ipam.Service
    - ipam.VLAN
    - ipam.VRF
    - tenancy.Tenant
    - tenancy.TenantGroup
    - users.User
    - virtualization.Cluster
    - virtualization.VirtualMachine
    """

    replaced_models = [
        Aggregate,
        DeviceRole,
        RackRole,
        Region,
        Role,
        Site,
    ]

    pk_change_models = [
        IPAddress,
        Prefix,
        TaggedItem,
    ]

    field_change_models = {
        CablePath: [
            "circuittermination",
            "consoleport",
            "consoleserverport",
            "interface",
            "powerfeed",
            "poweroutlet",
            "powerport",
        ],
        Circuit: ["termination_a", "termination_z", "terminations", "type"],
        Cluster: ["group", "type"],
        ConfigContext: ["schema"],
        ConfigContextSchema: ["device_set", "virtualmachine_set"],
        ContentType: [
            "computedfield_set",
            "configcontext_set",
            "configcontextschema_set",
            "customlink_set",
            "dcim_device_related",
            "dynamicgroup_set",
            "exporttemplate_set",
            "imageattachment_set",
            "note_set",
            "virtualization_virtualmachine_related",
        ],
        CustomField: ["choices", "label", "name"],
        CustomFieldChoice: ["field"],
        Device: [
            "consoleports",
            "consoleserverports",
            "devicebays",
            "device_role",
            "frontports",
            "inventoryitems",
            "local_context_data",
            "local_context_data_owner_content_type",
            "local_context_data_owner_object_id",
            "local_context_schema",
            "poweroutlets",
            "powerports",
            "rearports",
        ],
        DeviceRedundancyGroup: ["members"],
        DeviceType: [
            "consoleporttemplates",
            "consoleserverporttemplates",
            "devicebaytemplates",
            "frontporttemplates",
            "interfacetemplates",
            "instances",
            "poweroutlettemplates",
            "powerporttemplates",
            "rearporttemplates",
        ],
        FrontPortTemplate: ["rear_port"],
        GitRepository: ["slug", "_token", "username"],
        InventoryItem: ["child_items", "level", "lft", "rght", "tree_id"],
        IPAddress: ["assigned_object", "broadcast", "family", "prefix_length", "vrf"],
        Job: ["commit_default", "git_repository", "job_hook", "module_name", "name", "result", "source"],
        JobResult: ["completed", "created", "job_id", "job_kwargs", "logs", "obj_type", "schedule"],
        Location: ["powerpanels"],
        ObjectPermission: ["name", "object_types"],
        PowerOutletTemplate: ["power_port"],
        PowerPanel: ["powerfeeds"],
        PowerPort: ["poweroutlets"],
        PowerPortTemplate: ["poweroutlet_templates"],
        Prefix: ["family", "is_pool", "vrf"],
        Rack: ["group", "powerfeed_set", "reservations"],
        RackGroup: ["level", "lft", "powerpanel_set", "rght", "tree_id"],
        RearPort: ["frontports"],
        RearPortTemplate: ["frontport_templates"],
        Relationship: ["associations", "name"],
        RIR: ["aggregates"],
        ScheduledJob: ["job_class"],
        Secret: ["groups", "secretsgroupassociation_set"],
        SecretsGroup: ["device_set", "deviceredundancygroup_set", "gitrepository_set", "secretsgroupassociation_set"],
        SecretsGroupAssociation: ["group"],
        Service: ["ipaddresses", "name"],
        Status: [
            "circuits_circuit_related",
            "dcim_cable_related",
            "dcim_device_related",
            "dcim_deviceredundancygroup_related",
            "dcim_interface_related",
            "dcim_location_related",
            "dcim_powerfeed_related",
            "dcim_rack_related",
            "ipam_ipaddress_related",
            "ipam_prefix_related",
            "ipam_vlan_related",
            "virtualization_virtualmachine_related",
            "virtualization_vminterface_related",
        ],
        Tenant: ["group", "rackreservations"],
        TenantGroup: ["lft", "level", "rght", "tree_id"],
        User: ["changes", "note", "rackreservation_set"],
        VirtualMachine: [
            "local_context_data",
            "local_context_data_owner_content_type",
            "local_context_data_owner_object_id",
            "local_context_schema",
        ],
        VLAN: ["group"],
        VRF: ["enforce_unique"],
    }

    command.stdout.write(command.style.WARNING(">>> Running permission constraint checks..."))

    warnings = []

    for perm in ObjectPermission.objects.all():
        if not perm.object_types or not perm.constraints:
            continue
        constraints = perm.list_constraints()
        for ct in perm.object_types.all():
            model = ct.model_class()
            qs = model.objects.filter(*[models.Q(**c) for c in constraints])
            if not qs._query.where.children:
                continue

            for lookup in qs._query.where.children:
                lhs = lookup.lhs

                # Check if the left-hand side (lhs) of the lookup is a KeyTransform.
                # KeyTransform is used for accessing nested keys in JSON fields.
                if isinstance(lhs, KeyTransform):
                    # If lhs is a KeyTransform, it means we're dealing with a JSON field lookup usually a CustomField.
                    # `lhs.source_expressions` returns a list of `Col` objects representing the columns involved in the lookup.
                    cols = lhs.source_expressions
                    # - `col.field.name` gives the base field name (_custom_field_data).
                    # - `lhs.key_name` provides the specific custom field name (test_custom_field).
                    # Construct the field name by combining these with a double underscore.
                    suffix = f"__{lhs.key_name}"
                else:
                    # If lhs is not a KeyTransform, it is a direct column reference.
                    # Wrap lhs in a list to handle it uniformly in the next step.
                    cols = [lhs]
                    suffix = ""

                for col in cols:
                    field_name = f"{col.field.name}{suffix}"
                    related_model = col.target.related_model or col.target.model

                    if related_model in replaced_models:
                        cls = f"{related_model.__module__}.{related_model.__name__}"
                        warnings.append(
                            f"ObjectPermission '{perm}' (id: {perm.id}) has a constraint that references "
                            f"a model ({cls}) that will be migrated to a new model by the Nautobot 2.0 migration.\n"
                            + json.dumps(perm.constraints, indent=4)
                        )

                    if related_model in field_change_models:
                        if col.field.name in field_change_models[related_model]:
                            cls = f"{related_model.__module__}.{related_model.__name__}"
                            warnings.append(
                                f"ObjectPermission '{perm}' (id: {perm.id}) has a constraint that references "
                                f"a model field ({cls}.{field_name}) that may be changed by the Nautobot 2.0 migration.\n"
                                + json.dumps(perm.constraints, indent=4)
                            )

                    if field_name == "slug" and related_model is not GitRepository:
                        warnings.append(
                            f"ObjectPermission '{perm}' (id: {perm.id}) has a constraint that references "
                            f"a 'slug' field that will be deleted by the Nautobot 2.0 migration.\n"
                            + json.dumps(perm.constraints, indent=4)
                        )

                    if related_model in pk_change_models:
                        if isinstance(col.target, (models.fields.related.RelatedField, models.fields.UUIDField)):
                            cls = f"{related_model.__module__}.{related_model.__name__}"
                            warnings.append(
                                f"ObjectPermission '{perm}' (id: {perm.id}) has a constraint that references "
                                f"an object ({cls}) that may have its primary key changed by the Nautobot 2.0 migration.\n"
                                + json.dumps(perm.constraints, indent=4)
                            )

    if warnings:
        msg = """
One or more permission constraints may be affected by the Nautobot 2.0 migration.
These will not prevent the migration from running successfully, but they will have to be
updated manually after upgrading to Nautobot 2.0 to reference new models and/or values.
Please review the following warnings and make sure to document the objects referenced
by these constraints before upgrading:
        """
        command.stdout.write(command.style.WARNING(msg))
        command.stdout.write("\n\n".join(warnings))


class Command(BaseCommand):
    help = HELP_TEXT

    def create_parser(self, *args, **kwargs):
        """Custom parser that can display multiline help."""
        parser = super().create_parser(*args, **kwargs)
        parser.formatter_class = argparse.RawTextHelpFormatter
        return parser

    def handle(self, *args, **options):
        checks = [
            check_configcontext_uniqueness,
            check_exporttemplate_uniqueness,
            check_virtualchassis_uniqueness,
        ]
        errors = []

        for check in checks:
            func_name = check.__code__.co_name
            try:
                self.stdout.write(self.style.WARNING(f">>> Running check: {func_name}..."))
                check()
            except ValidationError as err:
                errors.append(err)

        try:
            check_interface_ipaddress_vrf_uniqueness(self)
        except ValidationError as err:
            errors.append(err)

        check_permissions_constraints(self)

        if errors:
            msg = "One or more pre-migration checks failed:\n"
            for err_item in errors:
                message_lines = err_item.message.splitlines()
                for line in message_lines:
                    msg += f"    {line}\n"
                msg += "\n"
            raise CommandError(msg)
        else:
            self.stdout.write(self.style.SUCCESS("All pre-migration checks passed."))
