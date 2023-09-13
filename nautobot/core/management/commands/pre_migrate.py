# TODO(jathan): This file MUST NOT be merged into Nautobot v2 (next).

import argparse
import json

from django.db import models
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from nautobot.dcim.models import DeviceRole, RackRole, VirtualChassis
from nautobot.ipam.models import Aggregate, IPAddress, Prefix, Role, Service
from nautobot.extras.models import (
    ConfigContext,
    ConfigContextSchema,
    CustomField,
    ExportTemplate,
    GitRepository,
    Job,
    ScheduledJob,
    TaggedItem,
)
from nautobot.users.models import ObjectPermission

HELP_TEXT = """
Performs pre-migration validation checks for Nautobot 2.0.

If the Nautobot 1.x instance cannot be upgraded, this command will exit uncleanly.
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


def check_permissions_constraints(command):
    """
    Check for permission constraints that are referencing an object field
    that will be migrated to a different model/field/value in 2.0 migrations.

    Objects that will be deleted in 2.0 are:
    - dcim.DeviceRole
    - dcim.RackRole
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
    """

    deleted_models = [
        Aggregate,
        DeviceRole,
        RackRole,
        Role,
    ]

    pk_change_models = [
        IPAddress,
        Prefix,
        ObjectPermission,
        TaggedItem,
    ]

    field_change_models = {
        GitRepository: ["slug"],
        Job: ["commit_default", "name", "module_name", "source", "git_repository"],
        CustomField: ["label"],
        ScheduledJob: ["kwargs", "user", "queue", "job_class", "name"],
        Service: ["name"],
        ObjectPermission: ["name"],
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
                related_model = lookup.lhs.target.related_model or lookup.lhs.target.model

                if related_model in deleted_models:
                    cls = f"{related_model.__module__}.{related_model.__name__}"
                    warnings.append(
                        f"ObjectPermission '{perm}' (id: {perm.id}) has a constraint that references "
                        f"a model ({cls}) that will be deleted by the Nautobot 2.0 migration."
                        + json.dumps(perm.constraints, indent=4)
                    )

                if related_model in field_change_models:
                    field_name = lookup.lhs.field.name
                    if field_name in field_change_models[related_model]:
                        cls = f"{related_model.__module__}.{related_model.__name__}"
                        warnings.append(
                            f"ObjectPermission '{perm}' (id: {perm.id}) has a constraint that references "
                            f"a model field ({cls}.{field_name}) that may be changed by the Nautobot 2.0 migration.\n"
                            + json.dumps(perm.constraints, indent=4)
                        )

                if lookup.lhs.field.name == "slug" and related_model is not GitRepository:
                    warnings.append(
                        f"ObjectPermission '{perm}' (id: {perm.id}) has a constraint that references "
                        f"a 'slug' field that will be deleted by the Nautobot 2.0 migration.\n"
                        + json.dumps(perm.constraints, indent=4)
                    )

                if related_model in pk_change_models:
                    if isinstance(lookup.lhs.target, (models.fields.related.RelatedField, models.fields.UUIDField)):
                        cls = f"{related_model.__module__}.{related_model.__name__}"
                        warnings.append(
                            f"ObjectPermission '{perm}' (id: {perm.id}) has a constraint that references "
                            f"an object ({cls}) that may have its primary key changed by the Nautobot 2.0 migration.\n"
                            + json.dumps(perm.constraints, indent=4)
                        )

    if warnings:
        msg = """
One or more permission constraints may be affected by the Nautobot 2.0 migration.
These permission constraints will have to be updated manually after upgrading to
Nautobot 2.0 to reference new models and/or values. Please review the following
warnings and make sure to document the objects referenced by these constraints
before upgrading:
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
