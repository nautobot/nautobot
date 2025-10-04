# noinspection PyUnresolvedReferences
import contextlib
import time

from django.apps import apps
from django.core.management.commands.migrate import Command as _Command
from django.db import models
from django.db.migrations.operations.fields import FieldOperation
from django.db.migrations.operations.models import ModelOperation

from nautobot.core.management import commands

# Overload deconstruct with our own.
models.Field.deconstruct = commands.custom_deconstruct


class Command(_Command):
    def migration_progress_callback(self, action, migration=None, fake=False):
        """
        Enhanced version of Django's built-in callback.

        Differences in behavior:
            - Measures and reports elapsed time whenever verbosity >= 1 (default value)
            - Measures and reports affected record counts and elapsed time per record where applicable at verbosity >= 2.
            - Aligns output to 80-character terminal width in most cases

        Examples:
            # nautobot-server migrate
            Running migrations:
              Applying dcim.0065_controller_capabilities_and_more...         OK        0.10s
              Applying wireless.0001_initial...                              OK        0.31s
              Applying dcim.0066_controllermanageddevicegroup_radio_profi... OK        0.12s

            # nautobot-server migrate -v=2 extras 0100
            Operations to perform:
              Target specific migration: 0100_fileproxy_job_result, from extras
            Running migrations:
              Rendering model states...                                      DONE     19.10s
              Unapplying ipam.0052_alter_ipaddress_index_together_and_mor... OK        0.10s
                Affected ipam.ipaddress                               75 rows  0.001s/record
                Affected ipam.prefix                                 184 rows  0.000s/record
                Affected ipam.vrf                                     20 rows  0.004s/record
              Unapplying ipam.0051_added_optional_vrf_relationship_to_vdc... OK        0.10s
                Affected ipam.vrf                                     20 rows  0.006s/record
                Affected ipam.vrfdeviceassignment                    140 rows  0.001s/record
              Unapplying virtualization.0030_alter_virtualmachine_local_c... OK        0.30s
                Affected virtualization.virtualmachine                 0 rows
                Affected virtualization.vminterface                    0 rows
              Unapplying virtualization.0029_add_role_field_to_interface_... OK        0.10s
                Affected virtualization.vminterface                    0 rows
        """
        if self.verbosity < 1:
            return

        if action in ["apply_start", "render_start", "unapply_start"]:
            self.start = time.monotonic()
            self.affected_models = set()
            self.affected_models_count = {}
            self.migration = migration
            if self.verbosity >= 2 and self.migration is not None:
                for operation in self.migration.operations:
                    if isinstance(operation, FieldOperation):
                        self.affected_models.add((self.migration.app_label, operation.model_name.lower()))
                    elif isinstance(operation, ModelOperation):
                        self.affected_models.add((self.migration.app_label, operation.name.lower()))

                for app_label, model_name in sorted(self.affected_models):
                    self.affected_models_count[f"{app_label}.{model_name}"] = 0
                    with contextlib.suppress(Exception):
                        model = apps.get_model(app_label, model_name)
                        self.affected_models_count[model._meta.label_lower] = model.objects.count()

            if action == "apply_start":
                msg = f"  Applying {str(migration)[:50]}..."
            elif action == "render_start":
                msg = "  Rendering model states..."
            else:
                msg = f"  Unapplying {str(migration)[:48]}..."
            self.stdout.write(f"{msg:<64}", ending="")
            self.stdout.flush()

        elif action in ["apply_success", "render_success", "unapply_success"]:
            elapsed = time.monotonic() - self.start
            outcome = "DONE" if action == "render_success" else "FAKED" if fake else "OK"
            self.stdout.write(self.style.SUCCESS(f" {outcome:<5} {elapsed: 8.2f}s"))
            if self.verbosity >= 2 and self.migration is not None:
                for app_label, model_name in sorted(self.affected_models):
                    if self.affected_models_count[f"{app_label}.{model_name}"] == 0:
                        with contextlib.suppress(Exception):
                            model = apps.get_model(app_label, model_name)
                            self.affected_models_count[model._meta.label_lower] = model.objects.count()

                for key, value in self.affected_models_count.items():
                    if value:
                        self.stdout.write(f"    Affected {key:<38} {value: 8} rows {elapsed / value:6.3f}s/record")
                    else:
                        self.stdout.write(f"    Affected {key:<38} {value: 8} rows")
