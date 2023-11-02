from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.http import QueryDict

from nautobot.core.api.renderers import NautobotCSVRenderer
from nautobot.core.api.utils import get_serializer_for_model
from nautobot.core.celery import app, register_jobs
from nautobot.core.utils.lookup import get_filterset_for_model
from nautobot.core.utils.requests import get_filterable_params_from_filter_params
from nautobot.extras.datasources import ensure_git_repository, git_repository_dry_run, refresh_datasource_content
from nautobot.extras.jobs import ChoiceVar, Job, ObjectVar, RunJobTaskFailed, StringVar
from nautobot.extras.models import ExportTemplate, GitRepository

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
        has_sensitive_variables = False

    def run(self, repository):
        job_result = self.job_result
        user = job_result.user

        self.logger.info(f'Creating/refreshing local copy of Git repository "{repository.name}"...')

        try:
            ensure_git_repository(repository, logger=self.logger)
            refresh_datasource_content("extras.gitrepository", repository, user, job_result, delete=False)
            # Given that the above succeeded, tell all workers (including ourself) to call ensure_git_repository()
            app.control.broadcast("refresh_git_repository", repository_pk=repository.pk, head=repository.current_head)
        finally:
            self.logger.info(f"Repository synchronization completed in {job_result.duration}")


class GitRepositoryDryRun(Job):
    """System Job to perform a dry run on a Git repository."""

    repository = ObjectVar(
        description="Git Repository to dry-run",
        label="Git Repository",
        model=GitRepository,
    )

    class Meta:
        name = "Git Repository: Dry-Run"
        has_sensitive_variables = False

    def run(self, repository):
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
        has_sensitive_variables = False
        # Exporting large querysets may take substantial processing time
        soft_time_limit = 1800
        time_limit = 2000

    def run(self, *, content_type, query_string="", export_format="csv", export_template=None):
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
        default_non_filter_params = ("export", "page", "per_page", "sort")
        filter_params = get_filterable_params_from_filter_params(
            query_params, default_non_filter_params, filterset_class()
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
            csv_data = renderer.render(serializer.data)
            self.create_file(filename + ".csv", csv_data)


jobs = [ExportObjectList, GitRepositorySync, GitRepositoryDryRun]
register_jobs(*jobs)
