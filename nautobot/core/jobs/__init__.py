import codecs
import contextlib
from io import BytesIO

from django.apps import apps as global_apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import (
    PermissionDenied,
)
from django.db import transaction
from django.db.models import Q
from django.http import QueryDict
from django.urls import reverse
from rest_framework import exceptions as drf_exceptions

from nautobot.core.api.exceptions import SerializerNotFound
from nautobot.core.api.parsers import NautobotCSVParser
from nautobot.core.api.renderers import NautobotCSVRenderer
from nautobot.core.api.utils import get_serializer_for_model
from nautobot.core.celery import app, register_jobs
from nautobot.core.exceptions import AbortTransaction
from nautobot.core.jobs.bulk_actions import BulkDeleteObjects, BulkEditObjects
from nautobot.core.jobs.cleanup import LogsCleanup
from nautobot.core.jobs.groups import RefreshDynamicGroupCacheJobButtonReceiver, RefreshDynamicGroupCaches
from nautobot.core.utils.lookup import get_filterset_for_model
from nautobot.core.utils.requests import get_filterable_params_from_filter_params
from nautobot.data_validation import models
from nautobot.data_validation.custom_validators import (
    BaseValidator,
    get_data_compliance_classes_from_git_repo,
    get_data_compliance_rules_map,
)
from nautobot.extras.datasources import (
    ensure_git_repository,
    git_repository_dry_run,
    refresh_datasource_content,
    refresh_job_code_from_repository,
)
from nautobot.extras.jobs import (
    BooleanVar,
    ChoiceVar,
    FileVar,
    Job,
    MultiChoiceVar,
    MultiObjectVar,
    ObjectVar,
    RunJobTaskFailed,
    StringVar,
    TextVar,
)
from nautobot.extras.models import ExportTemplate, GitRepository, SavedView
from nautobot.extras.plugins import CustomValidator, ValidationError
from nautobot.extras.registry import registry

name = "System Jobs"


class GitRepositorySync(Job):
    """
    System job to clone and/or pull a Git repository, then invoke `refresh_datasource_content()`.
    """

    repository = ObjectVar(
        description="Git Repository to pull and refresh",
        label="Git Repository",
        model=GitRepository,
    )

    class Meta:
        name = "Git Repository: Sync"
        description = "Clone and/or pull a Git repository, then refresh data sourced from this repository."
        has_sensitive_variables = False

    def run(self, repository):  # pylint:disable=arguments-differ
        job_result = self.job_result
        user = job_result.user

        self.logger.info(f'Creating/refreshing local copy of Git repository "{repository.name}"...')

        try:
            with transaction.atomic():
                ensure_git_repository(repository, logger=self.logger)
                refresh_datasource_content("extras.gitrepository", repository, user, job_result, delete=False)
                # Given that the above succeeded, tell all workers (including ourself) to call ensure_git_repository()
                app.control.broadcast(
                    "refresh_git_repository", repository_pk=repository.pk, head=repository.current_head
                )
                if job_result.duration:
                    self.logger.info("Repository synchronization completed in %s", job_result.duration)
        except Exception:
            job_result.log("Changes to database records have been reverted.")
            # Re-check-out previous commit if any
            repository.refresh_from_db()
            if repository.current_head:
                job_result.log(f"Attempting to revert local repository clone to commit {repository.current_head}")
                ensure_git_repository(repository, logger=self.logger, head=repository.current_head)
                refresh_job_code_from_repository(repository.slug, ignore_import_errors=True)
            raise


class GitRepositoryDryRun(Job):
    """System Job to perform a dry run on a Git repository."""

    repository = ObjectVar(
        description="Git Repository to dry-run",
        label="Git Repository",
        model=GitRepository,
    )

    class Meta:
        name = "Git Repository: Dry-Run"
        description = "Dry run of Git repository sync - will not update data sourced from this repository."
        has_sensitive_variables = False

    def run(self, repository):  # pylint:disable=arguments-differ
        job_result = self.job_result
        self.logger.info(f'Performing a Dry Run on Git repository "{repository.name}"...')

        try:
            git_repository_dry_run(repository, logger=self.logger)
        finally:
            self.logger.info(f"Repository dry run completed in {job_result.duration}")


class ExportObjectList(Job):
    """System Job to export a list of objects via CSV or ExportTemplate."""

    content_type = ObjectVar(
        model=ContentType,
        description="Type of objects to export",
        label="Content Type",
        query_params={"can_view": True},  # not adding "has_serializer": True as it might just support export-templates
    )
    query_string = StringVar(
        description='Filterset parameters to apply, in URL query parameter format e.g. "name=test&status=Active"',
        label="Filterset Parameters",
        default="",
        required=False,
    )
    export_format = ChoiceVar(
        choices=(("csv", "CSV"), ("yaml", "YAML")),
        description="Format to export to if not using an Export Template<br>"
        "(note, in core only <code>dcim | device type</code> supports YAML export at present)",
        default="csv",
        required=False,
    )
    export_template = ObjectVar(
        model=ExportTemplate,
        query_params={"content_type": "$content_type"},
        display_field="name",
        description="Export Template to use (if unspecified, will export to CSV/YAML as specified above)",
        label="Export Template",
        default=None,
        required=False,
    )

    class Meta:
        name = "Export Object List"
        description = "Export a list of objects to CSV or YAML, or render a specified Export Template."
        has_sensitive_variables = False
        # Exporting large querysets may take substantial processing time
        soft_time_limit = 1800
        time_limit = 2000

    def _get_saved_view_filter_params(self, query_params):
        """Extract filter params from saved view if applicable."""
        if "saved_view" in query_params and "all_filters_removed" not in query_params:
            saved_view_filters = SavedView.objects.get(pk=query_params["saved_view"]).config.get("filter_params", {})
            if len(query_params) > 1:
                # Retain only filters also present in query_params
                saved_view_filters = {key: value for key, value in saved_view_filters.items() if key in query_params}
            return saved_view_filters
        return {}

    def run(self, *, content_type, query_string="", export_format="csv", export_template=None):  # pylint:disable=arguments-differ
        if not self.user.has_perm(f"{content_type.app_label}.view_{content_type.model}"):
            self.logger.error('User "%s" does not have permission to view %s objects', self.user, content_type.model)
            raise PermissionDenied("User does not have view permissions on the requested content-type")

        model = content_type.model_class()

        # Start with all objects of the requested type
        queryset = model.objects.all()
        # Enforce user permissions
        queryset = queryset.restrict(self.user, "view")

        # Filter the queryset based on the provided query_string
        filterset_class = get_filterset_for_model(model)
        self.logger.debug("Found filterset class: `%s`", filterset_class.__name__)
        # TODO: ideally the ObjectListView should strip its non_filter_params (which may vary by view!)
        #       such that they never are even seen here.
        query_params = QueryDict(query_string)
        self.logger.debug("Parsed query_params: `%s`", query_params.dict())
        default_non_filter_params = (
            "all_filters_removed",
            "export",
            "page",
            "per_page",
            "saved_view",
            "sort",
            "table_changes_pending",
        )
        filter_params = self._get_saved_view_filter_params(query_params)
        filter_params.update(
            get_filterable_params_from_filter_params(query_params, default_non_filter_params, filterset_class())
        )
        self.logger.debug("Filterset params: `%s`", filter_params)
        filterset = filterset_class(filter_params, queryset)
        if not filterset.is_valid():
            self.logger.error("Invalid filters were specified: %s", filterset.errors)
            raise RunJobTaskFailed("Invalid query_string value for this content_type")
        queryset = filterset.qs
        object_count = queryset.count()

        filename = f"{settings.BRANDING_PREPENDED_FILENAME}{model._meta.verbose_name_plural.lower().replace(' ', '_')}"

        if export_template is not None:
            # Export templates
            if export_template.content_type != content_type:
                self.logger.error("ExportTemplate %s doesn't apply to %s", export_template, content_type)
                raise RunJobTaskFailed("ExportTemplate ContentType mismatch")
            self.logger.info(
                "Exporting %d objects via ExportTemplate. This may take some time.",
                object_count,
                extra={"object": export_template},
            )
            try:
                # export_template.render() consumes the whole queryset, so we don't have any way to do a progress bar.
                output = export_template.render(queryset)
            except Exception as err:
                self.logger.error("Error when rendering ExportTemplate: %s", err)
                raise
            if export_template.file_extension:
                filename += f".{export_template.file_extension}"
            self.create_file(filename, output)

        elif export_format == "yaml":
            # Device-type (etc.) YAML export
            if not hasattr(model, "to_yaml"):
                self.logger.error("Model %s doesn't support YAML export", content_type.model)
                raise ValueError("YAML export not supported for this content-type")
            self.logger.info("Exporting %d objects to YAML. This may take some time.", object_count)
            yaml_data = [obj.to_yaml() for obj in queryset]
            self.create_file(filename + ".yaml", "---\n".join(yaml_data))

        else:
            # Generic CSV export
            serializer_class = get_serializer_for_model(model)
            self.logger.debug("Found serializer class: `%s`", serializer_class.__name__)
            renderer = NautobotCSVRenderer()
            self.logger.info("Exporting %d objects to CSV. This may take some time.", object_count)
            # The force_csv=True attribute is a hack, but much easier than trying to construct a valid HttpRequest
            # object from scratch that passes all implicit and explicit assumptions in Django and DRF.
            serializer = serializer_class(queryset, many=True, context={"request": None}, force_csv=True)
            # Explicitly add UTF-8 BOM to the data so that Excel will understand non-ASCII characters correctly...
            csv_data = codecs.BOM_UTF8 + renderer.render(serializer.data).encode("utf-8")
            self.create_file(filename + ".csv", csv_data)


class ImportObjects(Job):
    """System Job to import CSV data to create a set of objects."""

    content_type = ObjectVar(
        model=ContentType,
        description="Type of objects to import",
        query_params={"can_add": True, "has_serializer": True},
    )
    csv_data = TextVar(label="CSV Data", required=False)
    csv_file = FileVar(label="CSV File", required=False)
    roll_back_if_error = BooleanVar(
        label="Rollback Changes on Failure",
        required=False,
        default=True,
        description="If an error is encountered when processing any row of data, rollback the entire import such that no data is imported.",
    )

    template_name = "system_jobs/import_objects.html"

    class Meta:
        name = "Import Objects"
        description = "Import objects from CSV-formatted data."
        has_sensitive_variables = False
        # Importing large files may take substantial processing time
        soft_time_limit = 1800
        time_limit = 2000

    def _perform_atomic_operation(self, data, serializer_class, queryset):
        new_objs = []
        with contextlib.suppress(AbortTransaction):
            with transaction.atomic():
                new_objs, validation_failed = self._perform_operation(data, serializer_class, queryset)
                if validation_failed:
                    raise AbortTransaction
                return new_objs, validation_failed
        # If validation failed return an empty list, since all objs created where rolled back
        self.logger.warning("Rolling back all %s records.", len(new_objs))
        return [], validation_failed

    def _perform_operation(self, data, serializer_class, queryset):
        new_objs = []
        validation_failed = False
        for row, entry in enumerate(data, start=1):
            serializer = serializer_class(data=entry, context={"request": None})
            if serializer.is_valid():
                try:
                    with transaction.atomic():
                        new_obj = serializer.save()
                        if not queryset.filter(pk=new_obj.pk).exists():
                            raise AbortTransaction()
                    self.logger.info('Row %d: Created record "%s"', row, new_obj, extra={"object": new_obj})
                    new_objs.append(new_obj)
                except AbortTransaction:
                    self.logger.error(
                        'Row %d: User "%s" does not have permission to create an object with these attributes',
                        row,
                        self.user,
                    )
                    validation_failed = True
            else:
                validation_failed = True
                for field, errs in serializer.errors.items():
                    for err in errs:
                        self.logger.error("Row %d: `%s`: `%s`", row, field, err)
        return new_objs, validation_failed

    def run(self, *, content_type, csv_data=None, csv_file=None, roll_back_if_error=False):  # pylint:disable=arguments-differ
        if not self.user.has_perm(f"{content_type.app_label}.add_{content_type.model}"):
            self.logger.error('User "%s" does not have permission to create %s objects', self.user, content_type.model)
            raise PermissionDenied("User does not have create permissions on the requested content-type")

        model = content_type.model_class()
        if model is None:
            self.logger.error(
                'Could not find the "%s.%s" data model. Perhaps an app is uninstalled?',
                content_type.app_label,
                content_type.model,
            )
            raise RunJobTaskFailed("Model not found")
        try:
            serializer_class = get_serializer_for_model(model)
        except SerializerNotFound:
            self.logger.error(
                'Could not find the "%s.%s" data serializer. Unable to process CSV for this model.',
                content_type.app_label,
                content_type.model,
            )
            raise
        queryset = model.objects.restrict(self.user, "add")

        if not csv_data and not csv_file:
            raise RunJobTaskFailed("Either csv_data or csv_file must be provided")
        if csv_file:
            # data_encoding is utf-8 and file_encoding is utf-8-sig
            # Bytes read from the original file are decoded according to file_encoding, and the result is encoded using data_encoding.
            csv_bytes = codecs.EncodedFile(csv_file, "utf-8", "utf-8-sig")
        else:
            csv_bytes = BytesIO(csv_data.encode("utf-8"))

        new_objs = []
        try:
            data = NautobotCSVParser().parse(
                stream=csv_bytes,
                parser_context={"request": None, "serializer_class": serializer_class},
            )
            self.logger.info("Processing %d rows of data", len(data))
            if roll_back_if_error:
                new_objs, validation_failed = self._perform_atomic_operation(data, serializer_class, queryset)
            else:
                new_objs, validation_failed = self._perform_operation(data, serializer_class, queryset)
        except drf_exceptions.ParseError as exc:
            validation_failed = True
            self.logger.error("`%s`", exc)

        if new_objs:
            self.logger.info(
                "Created %d %s object(s) from %d row(s) of data", len(new_objs), content_type.model, len(data)
            )
        else:
            self.logger.warning("No %s objects were created", content_type.model)

        if validation_failed:
            if roll_back_if_error:
                raise RunJobTaskFailed("CSV import not successful, all imports were rolled back, see logs")
            raise RunJobTaskFailed("CSV import not fully successful, see logs")


def get_data_compliance_rules():
    """Generate a list of Audit Ruleset classes that exist from the registry as well as from any Git Repositories."""
    validators = []
    for rule_sets in get_data_compliance_rules_map().values():
        validators.extend(rule_sets)

    # Get rules from Git Repositories
    for repo in GitRepository.objects.get_for_provided_contents("data_validation.data_compliance_rule"):
        validators.extend(get_data_compliance_classes_from_git_repo(repo))
    return validators


def get_data_compliance_choices():
    """Get data compliance choices from registry as well as from any Git Repositories."""
    choices = []
    for ruleset_class in get_data_compliance_rules():
        choices.append((ruleset_class.__name__, ruleset_class.__name__))

    choices.sort()
    return choices


def clean_compliance_rules_results_for_instance(instance, excluded_pks):
    """
    Delete data compliance results generated from runs of RunRegisteredDataComplianceRules job,
    which validates object against user-created rules.
    e.g. UniqueValidationRules, RegularExpressionValidationRules, MinMaxValidationRules, and RequiredValidationRules.

    The usage is that:
    If the instance is valid against all user-created rules, then the previous data compliance results of the instance are deleted.
    If the instance is invalid against any user-created rules, then this method deletes the existing data compliance results of the instance,
    and preserves only the data compliance result from the most recent job run by including the pk of the result in the `excluded_pks` list.

    Args:
        instance: The validated object to clean compliance results for.
        excluded_pks: List of primary keys of compliance results to exclude from deletion.
    """
    model_class = instance.__class__
    model_custom_validators = registry["plugin_custom_validators"][model_class._meta.label_lower]
    # Prep for compliance names to be deleted.
    compliance_class_names_to_be_deleted = []
    for cv in model_custom_validators:
        if issubclass(cv, BaseValidator):
            compliance_class_names_to_be_deleted.append(cv.__name__)

    excluded_pks = excluded_pks or []
    models.DataCompliance.objects.filter(
        object_id=instance.id,
        content_type=ContentType.objects.get_for_model(instance),
        compliance_class_name__in=compliance_class_names_to_be_deleted,
    ).exclude(pk__in=excluded_pks).delete()


class RunRegisteredDataComplianceRules(Job):
    """Run the validate function on all registered DataComplianceRule classes and, optionally, the built-in data validation rules."""

    class Meta:
        name = "Run Registered Data Compliance Rules"
        description = "Runs selected Data Compliance rule classes."
        has_sensitive_variables = False

    selected_data_compliance_rules = MultiChoiceVar(
        choices=get_data_compliance_choices,
        label="Select Data Compliance Rules",
        required=False,
        description="Not selecting any rules will run all rules listed.",
    )

    run_user_created_rules_in_report = BooleanVar(
        label="Run user created validation rules?", description="Include user created data validation rules in report."
    )

    def run(self, *args, **kwargs):
        """Run the validate function on all given DataComplianceRule classes."""
        selected_data_compliance_rules = kwargs.get("selected_data_compliance_rules", None)

        compliance_classes = get_data_compliance_rules()

        for compliance_class in sorted(
            compliance_classes, key=lambda x: x.model.split(".")
        ):  # sort by model.app_label and model.model_name
            if selected_data_compliance_rules and compliance_class.__name__ not in selected_data_compliance_rules:
                continue
            self.logger.info(f"Running {compliance_class.__name__}")
            app_label, model = compliance_class.model.split(".")
            for obj in global_apps.get_model(app_label, model).objects.iterator():
                ins = compliance_class(obj)
                ins.enforce = False
                ins.clean()

        run_user_created_rules_in_report = kwargs.get("run_user_created_rules_in_report", False)
        if run_user_created_rules_in_report:
            self.logger.info("Running user created data validation rules")
            self.report_for_validation_rules()

        result_url = reverse("data_validation:datacompliance_list")
        self.logger.info(f"View Data Compliance results [here]({result_url})")

    @staticmethod
    def report_for_validation_rules():
        """Run built-in data validation rules and add to report."""
        query = (
            Q(uniquevalidationrule__isnull=False)  # pylint: disable=unsupported-binary-operation
            | Q(regularexpressionvalidationrule__isnull=False)
            | Q(minmaxvalidationrule__isnull=False)
            | Q(requiredvalidationrule__isnull=False)
        )

        # Gather model classes that have any of the user created rules:
        # UniqueValidationRules, RegularExpressionValidationRules, MinMaxValidationRules, and RequiredValidationRules.
        model_classes = [ct.model_class() for ct in ContentType.objects.filter(query).distinct()]

        # Gather custom validators of user created rules
        validator_dicts = []
        for model_class in model_classes:
            model_custom_validators = registry["plugin_custom_validators"][model_class._meta.label_lower]
            # Get only subclasses of BaseValidator
            # BaseValidator is the validator that enforces the user created rules:
            # UniqueValidationRules, RegularExpressionValidationRules, MinMaxValidationRules, and RequiredValidationRules.
            # otherwise, we would get all validators (more than those dynamically created)
            validator_dicts.extend(
                [{cv: model_class} for cv in model_custom_validators if issubclass(cv, BaseValidator)]
            )

        # Run validation on existing objects and add to report
        for validator_dict in validator_dicts:
            for validator, class_name in validator_dict.items():
                if validator.clean == CustomValidator.clean:
                    continue

                for validated_object in class_name.objects.iterator():
                    try:
                        validator(validated_object).clean(exclude_disabled_rules=False)
                        clean_compliance_rules_results_for_instance(instance=validated_object, excluded_pks=[])
                    except ValidationError as error:
                        result = validator.get_compliance_result(
                            validator,
                            instance=validated_object,
                            message=error.messages[0],
                            attribute=next(iter(error.message_dict.keys())),
                            valid=False,
                        )
                        clean_compliance_rules_results_for_instance(instance=validated_object, excluded_pks=[result.pk])


class ValidateModelData(Job):
    """Clean and validate data in all records of a given content type(s)."""

    class Meta:
        name = "Validate Model Data"
        description = "Run `full_clean()` against all records of a given type(s) to check for data validity."
        has_sensitive_variables = False
        read_only = True
        # Validating large amounts of data may take substantial processing time
        soft_time_limit = 1800
        time_limit = 2000

    content_types = MultiObjectVar(
        model=ContentType,
        description="Type(s) of objects to validate.",
        label="Content Types",
        query_params={"can_view": True},
        required=True,
    )
    verbose = BooleanVar(default=False, label="Verbose output?")

    def run(self, *, content_types, verbose=False):  # pylint:disable=arguments-differ
        for content_type in content_types:
            model = content_type.model_class()
            if model is None:
                self.fail(
                    "Couldn't locate Python model for content-type %s.%s",
                    content_type.app_label,
                    content_type.model,
                )
                continue

            try:
                records = model.objects.restrict(self.user, "view")
            except AttributeError:  # Not a RestrictedQuerySet?
                if self.user.is_superuser:  # i.e., permissions exempt
                    records = model.objects.all()
                else:
                    self.fail("Unable to apply access permissions to %s.%s", content_type.app_label, content_type.model)

            if not records.exists():
                self.logger.warning("No %s found", model._meta.verbose_name_plural)
                continue

            self.logger.info("Validating %d %s", records.count(), model._meta.verbose_name_plural)
            for record in records.iterator():
                try:
                    record.full_clean()
                    if verbose:
                        self.logger.success("Validated successfully", extra={"object": record})
                except ValidationError as err:
                    self.fail("Validation error: `%s`", err, extra={"object": record})


jobs = [
    BulkDeleteObjects,
    BulkEditObjects,
    ExportObjectList,
    GitRepositorySync,
    GitRepositoryDryRun,
    ImportObjects,
    LogsCleanup,
    RefreshDynamicGroupCaches,
    RefreshDynamicGroupCacheJobButtonReceiver,
    RunRegisteredDataComplianceRules,
    ValidateModelData,
]
register_jobs(*jobs)
