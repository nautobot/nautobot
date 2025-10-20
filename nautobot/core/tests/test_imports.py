import ast
import os
import re
from unittest import TestCase

BLACKLIST_FILE_PATTERNS = [
    r"^models",
    r"^tables",
    r"^forms",
    r"^filters",
    r"^api",
    r"^tests",
    r"^views",
    r"^migrations",
    r"^test_jobs",
    r"^management",
    r"^jobs",
    r"^checks",
    r"^factory",
    r"^signals",
    r"^graphql",
]

BLACKLIST_FUNC_PATTERNS = [
    r".*__init__.*",
]

BLACKLIST_FILE_REGEX = re.compile("|".join(BLACKLIST_FILE_PATTERNS), re.IGNORECASE)
BLACKLIST_FUNC_REGEX = re.compile("|".join(BLACKLIST_FUNC_PATTERNS))

ALWAYS_INCLUDE_PATH_PATTERNS = [
    "nautobot/core/views",
    "nautobot/core/models",
    "nautobot/core/tables",
    "nautobot/core/filters",
    "nautobot/core/forms",
    "nautobot/core/api",
    "nautobot/core/jobs",
]

KNOWN_SKIPPED_IMPORTS = [
    "nautobot.circuits.apps.CircuitsConfig",
    "nautobot.circuits.choices.CircuitStatusChoices",
    "nautobot.cloud.apps.CloudConfig",
    "nautobot.core.admin.ConfigAdmin",
    "nautobot.core.admin.ConfigForm",
    "nautobot.core.authentication.ObjectPermissionBackend",
    "nautobot.core.authentication.RemoteUserBackend",
    "nautobot.core.authentication.assign_groups_to_user",
    "nautobot.core.authentication.assign_permissions_to_user",
    "nautobot.core.celery.backends.NautobotDatabaseBackend",
    "nautobot.core.celery.control.discard_git_repository",
    "nautobot.core.celery.control.refresh_git_repository",
    "nautobot.core.celery.log.NautobotDatabaseHandler",
    "nautobot.core.celery.schedulers.NautobotDatabaseScheduler",
    "nautobot.core.celery.schedulers.NautobotScheduleEntry",
    "nautobot.core.celery.task.NautobotTask",
    "nautobot.core.choices.ChoiceSetMeta",
    "nautobot.core.context_processors.get_saml_idp",
    "nautobot.core.context_processors.sso_auth",
    "nautobot.core.events.exceptions.EventBrokerError",
    "nautobot.core.events.exceptions.EventBrokerImproperlyConfigured",
    "nautobot.core.events.exceptions.EventBrokerNotFound",
    "nautobot.core.middleware.ExceptionHandlingMiddleware",
    "nautobot.core.middleware.ExternalAuthMiddleware",
    "nautobot.core.middleware.ObjectChangeMiddleware",
    "nautobot.core.middleware.RemoteUserMiddleware",
    "nautobot.core.middleware.UserDefinedTimeZoneMiddleware",
    "nautobot.core.settings.UI_RACK_VIEW_TRUNCATE_FUNCTION",
    "nautobot.core.settings.silk_request_logging_intercept_logic",
    "nautobot.core.settings.silk_user_permissions",
    "nautobot.core.settings_funcs.is_truthy",
    "nautobot.core.settings_funcs.ldap_auth_enabled",
    "nautobot.core.settings_funcs.parse_redis_connection",
    "nautobot.core.settings_funcs.remote_auth_enabled",
    "nautobot.core.settings_funcs.setup_structlog_logging",
    "nautobot.core.settings_funcs.sso_auth_enabled",
    "nautobot.core.tasks.get_releases",
    "nautobot.core.templatetags.bootstrapped_goodies_tags.custom_field_rendering",
    "nautobot.core.templatetags.bootstrapped_goodies_tags.fieldset_column_width",
    "nautobot.core.templatetags.bootstrapped_goodies_tags.form_fieldset_column_width",
    "nautobot.core.templatetags.bootstrapped_goodies_tags.language_selector",
    "nautobot.core.templatetags.bootstrapped_goodies_tags.render_app_description",
    "nautobot.core.templatetags.bootstrapped_goodies_tags.render_app_label",
    "nautobot.core.templatetags.bootstrapped_goodies_tags.render_app_name",
    "nautobot.core.templatetags.bootstrapped_goodies_tags.render_with_template_if_exist",
    "nautobot.core.templatetags.helpers.CaptureasNode",
    "nautobot.core.testing.context.load_event_broker_override_settings",
    "nautobot.core.ui.breadcrumbs.WithStr",
    "nautobot.core.utils.logging.clean_html",
    "nautobot.core.utils.module_loading.check_name_safe_to_import_privately",
    "nautobot.core.utils.module_loading.clear_module_from_sys_modules",
    "nautobot.core.utils.module_loading.import_modules_privately",
    "nautobot.core.utils.patch_social_django.patch_django_storage",
    "nautobot.dcim.apps.DCIMConfig",
    "nautobot.dcim.choices.CableStatusChoices",
    "nautobot.dcim.choices.ControllerCapabilitiesChoices",
    "nautobot.dcim.choices.DeviceRedundancyGroupStatusChoices",
    "nautobot.dcim.choices.DeviceStatusChoices",
    "nautobot.dcim.choices.InterfaceRedundancyGroupStatusChoices",
    "nautobot.dcim.choices.InterfaceStatusChoices",
    "nautobot.dcim.choices.LocationDataToContactActionChoices",
    "nautobot.dcim.choices.LocationStatusChoices",
    "nautobot.dcim.choices.ModuleStatusChoices",
    "nautobot.dcim.choices.RackStatusChoices",
    "nautobot.dcim.choices.VirtualDeviceContextStatusChoices",
    "nautobot.dcim.elevations.RackElevationSVG",
    "nautobot.dcim.fields.ASNField",
    "nautobot.dcim.fields.JSONPathField",
    "nautobot.dcim.lookups.PathContains",
    "nautobot.dcim.ui.RackBreadcrumbs",
    "nautobot.dcim.utils.cable_status_color_css",
    "nautobot.dcim.utils.compile_path_node",
    "nautobot.dcim.utils.convert_watts_to_va",
    "nautobot.dcim.utils.decompile_path_node",
    "nautobot.dcim.utils.get_all_network_driver_mappings",
    "nautobot.dcim.utils.get_network_driver_mapping_tool_names",
    "nautobot.dcim.utils.object_to_path_node",
    "nautobot.dcim.utils.path_node_to_object",
    "nautobot.dcim.utils.render_software_version_and_image_files",
    "nautobot.dcim.utils.validate_interface_tagged_vlans",
    "nautobot.docs.macros.define_env",
    "nautobot.extras.admin.FileProxyAdmin",
    "nautobot.extras.admin.FileProxyForm",
    "nautobot.extras.admin.JobResultAdmin",
    "nautobot.extras.admin.order_content_types",
    "nautobot.extras.apps.ExtrasConfig",
    "nautobot.extras.choices.ContactAssociationRoleChoices",
    "nautobot.extras.choices.ContactAssociationStatusChoices",
    "nautobot.extras.choices.DynamicGroupTypeChoices",
    "nautobot.extras.choices.JobQueueTypeChoices",
    "nautobot.extras.choices.MetadataTypeDataTypeChoices",
    "nautobot.extras.context_managers.deferred_change_logging_for_bulk_operation",
    "nautobot.extras.datasources.git.delete_git_config_context_schemas",
    "nautobot.extras.datasources.git.delete_git_config_contexts",
    "nautobot.extras.datasources.git.delete_git_export_templates",
    "nautobot.extras.datasources.git.delete_git_graphql_queries",
    "nautobot.extras.datasources.git.enqueue_git_repository_diff_origin_and_local",
    "nautobot.extras.datasources.git.enqueue_git_repository_helper",
    "nautobot.extras.datasources.git.enqueue_pull_git_repository_and_refresh_data",
    "nautobot.extras.datasources.git.ensure_git_repository",
    "nautobot.extras.datasources.git.get_repo_from_url_to_path_and_from_branch",
    "nautobot.extras.datasources.git.git_repository_dry_run",
    "nautobot.extras.datasources.git.import_config_context",
    "nautobot.extras.datasources.git.import_config_context_schema",
    "nautobot.extras.datasources.git.import_local_config_context",
    "nautobot.extras.datasources.git.refresh_git_config_context_schemas",
    "nautobot.extras.datasources.git.refresh_git_config_contexts",
    "nautobot.extras.datasources.git.refresh_git_export_templates",
    "nautobot.extras.datasources.git.refresh_git_graphql_queries",
    "nautobot.extras.datasources.git.refresh_git_jobs",
    "nautobot.extras.datasources.git.refresh_job_code_from_repository",
    "nautobot.extras.datasources.git.update_git_config_context_schemas",
    "nautobot.extras.datasources.git.update_git_config_contexts",
    "nautobot.extras.datasources.git.update_git_export_templates",
    "nautobot.extras.datasources.git.update_git_graphql_queries",
    "nautobot.extras.datasources.registry.get_datasource_content_choices",
    "nautobot.extras.datasources.registry.get_datasource_contents",
    "nautobot.extras.datasources.registry.refresh_datasource_content",
    "nautobot.extras.datasources.utils.files_from_contenttype_directories",
    "nautobot.extras.group_sync.group_sync",
    "nautobot.extras.health_checks.DatabaseBackend",
    "nautobot.extras.health_checks.MigrationsBackend",
    "nautobot.extras.health_checks.NautobotHealthCheckBackend",
    "nautobot.extras.health_checks.RedisBackend",
    "nautobot.extras.health_checks.RedisHealthCheck",
    "nautobot.extras.homepage.get_changelog",
    "nautobot.extras.homepage.get_job_results",
    "nautobot.extras.managers.JobResultManager",
    "nautobot.extras.managers.ScheduledJobsManager",
    "nautobot.extras.plugins.exceptions.PluginError",
    "nautobot.extras.plugins.exceptions.PluginImproperlyConfigured",
    "nautobot.extras.plugins.exceptions.PluginNotFound",
    "nautobot.extras.plugins.utils.get_sso_backend_name",
    "nautobot.extras.plugins.utils.import_object",
    "nautobot.extras.plugins.utils.load_plugin",
    "nautobot.extras.plugins.utils.load_plugins",
    "nautobot.extras.querysets.ConfigContextQuerySet",
    "nautobot.extras.querysets.DynamicGroupMembershipQuerySet",
    "nautobot.extras.querysets.DynamicGroupQuerySet",
    "nautobot.extras.querysets.JobQuerySet",
    "nautobot.extras.querysets.NotesQuerySet",
    "nautobot.extras.querysets.ScheduledJobExtendedQuerySet",
    "nautobot.extras.registry.Registry",
    "nautobot.extras.registry.register_datasource_contents",
    "nautobot.extras.secrets.providers.EnvironmentVariableSecretsProvider",
    "nautobot.extras.secrets.providers.TextFileSecretsProvider",
    "nautobot.extras.tasks.delete_custom_field_data",
    "nautobot.extras.tasks.process_webhook",
    "nautobot.extras.tasks.provision_field",
    "nautobot.extras.tasks.update_custom_field_choice_data",
    "nautobot.extras.templatetags.registry.RegistryNode",
    "nautobot.extras.templatetags.registry.do_registry",
    "nautobot.extras.utils.bulk_delete_with_bulk_change_logging",
    "nautobot.extras.utils.change_logged_models_queryset",
    "nautobot.extras.utils.fixup_dynamic_group_group_types",
    "nautobot.extras.utils.fixup_filterset_query_params",
    "nautobot.extras.utils.get_job_queue",
    "nautobot.extras.utils.get_job_queue_worker_count",
    "nautobot.extras.utils.run_kubernetes_job_and_return_job_result",
    "nautobot.extras.webhooks.enqueue_webhooks",
    "nautobot.ipam.apps.IPAMConfig",
    "nautobot.ipam.choices.IPAddressStatusChoices",
    "nautobot.ipam.choices.PrefixStatusChoices",
    "nautobot.ipam.choices.VLANStatusChoices",
    "nautobot.ipam.choices.VRFStatusChoices",
    "nautobot.ipam.formfields.PrefixFilterFormField",
    "nautobot.ipam.lookups.EndsWith",
    "nautobot.ipam.lookups.Exact",
    "nautobot.ipam.lookups.IEndsWith",
    "nautobot.ipam.lookups.IExact",
    "nautobot.ipam.lookups.IPDetails",
    "nautobot.ipam.lookups.IRegex",
    "nautobot.ipam.lookups.IStartsWith",
    "nautobot.ipam.lookups.NetContained",
    "nautobot.ipam.lookups.NetContainedOrEqual",
    "nautobot.ipam.lookups.NetContains",
    "nautobot.ipam.lookups.NetContainsOrEquals",
    "nautobot.ipam.lookups.NetEquals",
    "nautobot.ipam.lookups.NetFamily",
    "nautobot.ipam.lookups.NetHost",
    "nautobot.ipam.lookups.NetHostContained",
    "nautobot.ipam.lookups.NetIn",
    "nautobot.ipam.lookups.NetworkFieldMixin",
    "nautobot.ipam.lookups.Regex",
    "nautobot.ipam.lookups.StartsWith",
    "nautobot.ipam.lookups.StringMatchMixin",
    "nautobot.ipam.lookups.get_ip_info",
    "nautobot.ipam.lookups.py_to_hex",
    "nautobot.ipam.mixins.LocationToLocationsQuerySetMixin",
    "nautobot.ipam.querysets.BaseNetworkQuerySet",
    "nautobot.ipam.querysets.IPAddressQuerySet",
    "nautobot.ipam.querysets.PrefixQuerySet",
    "nautobot.ipam.querysets.RIRQuerySet",
    "nautobot.ipam.querysets.VLANQuerySet",
    "nautobot.ipam.ui.AddChildPrefixButton",
    "nautobot.ipam.ui.AddIPAddressButton",
    "nautobot.ipam.ui.IPAddressTablePanel",
    "nautobot.ipam.ui.PrefixChildTablePanel",
    "nautobot.ipam.ui.PrefixKeyValueOverrideValueTablePanel",
    "nautobot.ipam.ui.PrefixObjectFieldsPanel",
    "nautobot.ipam.utils.testing.create_ips",
    "nautobot.ipam.utils.testing.create_prefixes",
    "nautobot.ipam.utils.testing.create_prefixes_and_ips",
    "nautobot.ipam.utils.testing.maybe_random_instance",
    "nautobot.ipam.utils.testing.maybe_subdivide",
    "nautobot.ipam.validators.MaxPrefixLengthValidator",
    "nautobot.ipam.validators.MinPrefixLengthValidator",
    "nautobot.ipam.validators.prefix_validator",
    "nautobot.project-static.docs.macros.define_env",
    "nautobot.tenancy.apps.TenancyConfig",
    "nautobot.users.admin.ActionListFilter",
    "nautobot.users.admin.GroupAdmin",
    "nautobot.users.admin.GroupObjectPermissionInline",
    "nautobot.users.admin.LogEntryAdmin",
    "nautobot.users.admin.ObjectPermissionAdmin",
    "nautobot.users.admin.ObjectPermissionForm",
    "nautobot.users.admin.ObjectPermissionInline",
    "nautobot.users.admin.ObjectTypeListFilter",
    "nautobot.users.admin.TokenAdmin",
    "nautobot.users.admin.TokenAdminForm",
    "nautobot.users.admin.UserAdmin",
    "nautobot.users.admin.UserObjectPermissionInline",
    "nautobot.users.apps.UsersConfig",
    "nautobot.users.utils.serialize_user_without_config_and_views",
    "nautobot.virtualization.apps.VirtualizationConfig",
    "nautobot.virtualization.choices.VMInterfaceStatusChoices",
    "nautobot.virtualization.choices.VirtualMachineStatusChoices",
    "nautobot.wireless.apps.WirelessConfig",
    "nautobot.wireless.choices.RadioProfileChannelWidthChoices",
    "nautobot.wireless.choices.RadioProfileFrequencyChoices",
    "nautobot.wireless.choices.RadioProfileRegulatoryDomainChoices",
    "nautobot.wireless.choices.SupportedDataRateStandardChoices",
    "nautobot.wireless.choices.WirelessNetworkAuthenticationChoices",
    "nautobot.wireless.choices.WirelessNetworkModeChoices",
]


def is_blacklisted_file(filepath):
    """Determine if a file is blacklisted based on its path or name."""
    rel_path = os.path.relpath(filepath)
    for include_path in ALWAYS_INCLUDE_PATH_PATTERNS:
        if rel_path.startswith(include_path):
            return False
    parts = os.path.normpath(filepath).split(os.sep)
    for part in parts:
        if BLACKLIST_FILE_REGEX.match(part):
            return True
    return False


def is_blacklisted_func(name):
    """Determine if a function or class is blacklisted based on its name."""
    return BLACKLIST_FUNC_REGEX.match(name)


def find_func_or_class(filepath, remove_dir_prefix):
    """Find all top-level functions and classes defined in a given file."""
    with open(filepath, "r") as f:
        tree = ast.parse(f.read(), filename=filepath)

    defined = set()
    imported = set()

    # Compute the module path for FQN
    module_path = filepath.replace(remove_dir_prefix, "").replace(".py", "").replace("/", ".")

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.asname or alias.name)

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            name = node.name
            fqn = f"{module_path}.{name}"
            if name.startswith("_"):
                continue
            if name in imported:
                continue
            if is_blacklisted_func(name) or is_blacklisted_func(fqn):
                continue
            if fqn in KNOWN_SKIPPED_IMPORTS:
                continue
            defined.add(name)

    return defined


def find_already_imported_in_apps(apps_dir):
    """Find all functions and classes already imported in the nautobot.apps directory."""
    imported = set()
    for fname in os.listdir(apps_dir):
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(apps_dir, fname)
        if not os.path.isfile(fpath):
            continue
        with open(fpath, "r") as f:
            try:
                tree = ast.parse(f.read(), filename=fpath)
            except (SyntaxError, UnicodeDecodeError, ValueError):
                continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported.add(alias.asname or alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.asname or alias.name)
    return imported


def find_all_python_files(root_dir):
    """Recursively find all Python files under a given root directory, excluding blacklisted files/folders."""
    py_files = []
    for root, _, files in os.walk(root_dir):
        # Skip blacklisted folders
        if any(BLACKLIST_FILE_REGEX.match(part) for part in os.path.normpath(root).split(os.sep)):
            continue
        for fname in files:
            if not fname.endswith(".py"):
                continue
            # Skip blacklisted files
            if BLACKLIST_FILE_REGEX.match(fname):
                continue
            py_files.append(os.path.join(root, fname))
    return py_files


def main():
    """Main function to find missing imports in nautobot.apps."""
    nautobot_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    remove_dir_prefix = os.path.dirname(nautobot_dir) + "/"

    apps_dir = os.path.join(nautobot_dir, "apps")
    imported_symbols = find_already_imported_in_apps(apps_dir)
    py_files = find_all_python_files(nautobot_dir)
    output = []

    for source_file in py_files:
        # Skip files in nautobot/apps
        if os.path.commonpath([source_file, apps_dir]) == apps_dir:
            continue
        if is_blacklisted_file(source_file):
            continue
        defined_symbols = find_func_or_class(source_file, remove_dir_prefix)
        missing_exports = defined_symbols - imported_symbols
        if missing_exports:
            source_file = source_file.replace(remove_dir_prefix, "").replace(".py", "").replace("/", ".")
            output.append(f"\nfrom {source_file} import (")
            for symbol in sorted(missing_exports):
                output.append(f"  {symbol},")
            output.append(")")
    return "\n".join(output)


class ImportTestCase(TestCase):
    """Test case to ensure nautobot.apps contains all relevant imports."""

    def test_imports(self):
        output = main()
        error_message = (
            f"There are missing imports in nautobot.apps. If not appropriate as an import, "
            f"update `KNOWN_SKIPPED_IMPORTS`, or add them to `nautobot.apps.*`. Missing imports would be: \n{output}"
        )
        self.assertEqual(output, "", error_message)


if __name__ == "__main__":
    """Use this to print out missing imports outside of the test framework."""
    print(main())
