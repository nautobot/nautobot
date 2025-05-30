import codecs
import contextlib
from io import BytesIO

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import (
    PermissionDenied,
)
from django.db import transaction
from django.http import QueryDict
from rest_framework import exceptions as drf_exceptions

from nautobot.core.api.exceptions import SerializerNotFound
from nautobot.core.api.parsers import NautobotCSVParser
from nautobot.core.api.renderers import NautobotCSVRenderer
from nautobot.core.api.utils import get_serializer_for_model
from nautobot.core.celery import app, register_jobs
from nautobot.core.exceptions import AbortTransaction
from nautobot.core.jobs.bulk_actions import BulkDeleteObjects, BulkEditObjects
from nautobot.core.jobs.cleanup import LogsCleanup
from nautobot.core.jobs.groups import RefreshDynamicGroupCaches
from nautobot.core.utils.lookup import get_filterset_for_model
from nautobot.core.utils.requests import get_filterable_params_from_filter_params
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
    ObjectVar,
    RunJobTaskFailed,
    StringVar,
    TextVar,
)
from nautobot.extras.models import ExportTemplate, GitRepository, SavedView

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


jobs = [
    BulkDeleteObjects,
    BulkEditObjects,
    ExportObjectList,
    GitRepositorySync,
    GitRepositoryDryRun,
    ImportObjects,
    LogsCleanup,
    RefreshDynamicGroupCaches,
]
register_jobs(*jobs)
