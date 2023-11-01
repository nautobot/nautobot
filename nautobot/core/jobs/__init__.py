from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.http import QueryDict

from nautobot.core.api.renderers import NautobotCSVRenderer
from nautobot.core.api.utils import get_serializer_for_model
from nautobot.core.celery import app, register_jobs
from nautobot.core.utils.lookup import get_filterset_for_model
from nautobot.core.utils.requests import get_filterable_params_from_filter_params
from nautobot.extras.datasources import ensure_git_repository, git_repository_dry_run, refresh_datasource_content
from nautobot.extras.jobs import Job, ObjectVar, StringVar
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
    export_template = ObjectVar(
        model=ExportTemplate,
        query_params={"content_type": "$content_type"},
        display_field="name",
        description="Export Template to use (if unspecified, will export to generic CSV instead)",
        label="Export Template",
        default=None,
        required=False,
    )

    class Meta:
        name = "Export Object List"
        has_sensitive_variables = False
        # Exporting large querysets may take substantial processing time
        soft_time_limit = 1500
        time_limit = 3000

    def run(self, *, content_type, query_string="", export_template=None):
        if not self.user.has_perm(f"{content_type.app_label}.view_{content_type.model}"):
            self.logger.error('User "%s" does not have permission to view %s objects', self.user, content_type.model)
            raise Exception("User does not have view permissions on the requested content-type")

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
        self.logger.debug("Filter params: `%s`", filter_params)
        filterset = filterset_class(filter_params, queryset)
        if not filterset.is_valid():
            self.logger.error("Invalid filters were specified: %s", filterset.errors)
            raise Exception("Invalid query_string value for this content_type")
        queryset = filterset.qs
        object_count = queryset.count()

        filename = f"{settings.BRANDING_PREPENDED_FILENAME}{model._meta.verbose_name_plural.lower().replace(' ', '_')}"

        # If query_string == "export", then query_params["export"] will be [""], rather than [] or "" as might expect
        if export_template is None and query_params.get("export", [""]) != [""]:
            try:
                export_template = ExportTemplate.objects.get(content_type=content_type, name=query_params.get("export"))
            except ExportTemplate.DoesNotExist as err:
                self.logger.error(
                    "ExportTemplate %s not found for content-type %s", query_params.get("export"), content_type
                )
                raise Exception("Requested export-template not found") from err

        if export_template is not None:
            # Export templates
            if export_template.content_type != content_type:
                self.logger.error("ExportTemplate %s doesn't apply to %s", export_template, content_type)
                raise Exception("ExportTemplate ContentType mismatch")
            self.logger.info(
                "Exporting %d objects via ExportTemplate. This may take some time.",
                object_count,
                extra={"object": export_template},
            )
            try:
                # export_template.render() consumes the whole queryset, so we don't have any way to do a progress bar.
                output = export_template.render(queryset)
            except Exception as e:
                self.logger.error("Error when rendering ExportTemplate: %s", e)
                raise
            if export_template.file_extension:
                filename += f".{export_template.file_extension}"
            self.create_file(filename, output)

        elif "export" in query_params and hasattr(model, "to_yaml"):
            # Device-type (etc.) YAML export
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
