"""Git data source functionality."""
import logging
import os
import re

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from django_rq import job

import yaml

from dcim.models import Region, Site, DeviceRole, Platform
from extras.choices import LogLevelChoices, JobResultStatusChoices
from extras.models import ConfigContext, ExportTemplate, GitRepository, JobResult, Tag
from extras.registry import DatasourceContent, register_datasource_contents
from utilities.git import GitRepo
from utilities.utils import copy_safe_request
from virtualization.models import ClusterGroup, Cluster
from tenancy.models import TenantGroup, Tenant
from .registry import refresh_datasource_content

logger = logging.getLogger(f"netbox.datasources.git")


def enqueue_pull_git_repository_and_refresh_data(repository, request):
    """
    Convenience wrapper for JobResult.enqueue_job() to enqueue the pull_git_repository_and_refresh_data job.
    """
    git_repository_content_type = ContentType.objects.get_for_model(GitRepository)
    JobResult.enqueue_job(
        pull_git_repository_and_refresh_data,
        repository.name,
        git_repository_content_type,
        request.user,
        repository_pk=repository.pk,
        request=copy_safe_request(request),
    )


@job('default')
def pull_git_repository_and_refresh_data(repository_pk, request, job_result):
    """
    Worker function to clone and/or pull a Git repository into NetBox, then invoke refresh_datasource_content().
    """
    repository_record = GitRepository.objects.get(pk=repository_pk)
    if not repository_record:
        job_result.log(
            f"No GitRepository {repository_pk} found!", level_choice=LogLevelChoices.LOG_FAILURE, logger=logger
        )
        job_result.set_status(JobResultStatusChoices.STATUS_ERRORED)
        job_result.save()
        return

    job_result.log(f'Creating/refreshing local copy of Git repository "{repository_record.name}"...', logger=logger)
    job_result.set_status(JobResultStatusChoices.STATUS_RUNNING)
    job_result.save()

    try:
        if not os.path.exists(settings.GIT_ROOT):
            os.makedirs(settings.GIT_ROOT)

        ensure_git_repository(
            repository_record,
            job_result=job_result,
            logger=logger,
        )

        refresh_datasource_content('extras.GitRepository', repository_record, request, job_result)

    except Exception as exc:
        job_result.log(
            f"Error while refreshing {repository_record.name}: {exc}", level_choice=LogLevelChoices.LOG_FAILURE
        )
        job_result.set_status(JobResultStatusChoices.STATUS_ERRORED)

    finally:
        if job_result.status not in JobResultStatusChoices.TERMINAL_STATE_CHOICES:
            if job_result.check_for_failed_logs():
                job_result.set_status(JobResultStatusChoices.STATUS_FAILED)
            else:
                job_result.set_status(JobResultStatusChoices.STATUS_COMPLETED)
        job_result.log(
            f"Repository synchronization completed in {job_result.duration}",
            level_choice=LogLevelChoices.LOG_INFO,
            logger=logger,
        )
        job_result.save()


def ensure_git_repository(repository_record, job_result=None, logger=None, head=None):
    """Ensure that the given Git repo is present, up-to-date, and has the correct branch selected.

    Note that this function may be called independently of the `pull_git_repository_and_refresh_data` job,
    such as to ensure that different NetBox instances and/or worker instances all have a local copy of the same HEAD.

    Args:
      repository_record (GitRepository)
      job_result (JobResult): Optional JobResult to store results into.
      logger (logging.Logger): Optional Logger to additionally log results to.
      head (str): Optional Git commit hash to check out instead of pulling branch latest.
    """

    # Inject token into source URL if necessary
    from_url = repository_record.remote_url
    token = repository_record._token
    if token and token not in from_url:
        from_url = re.sub('//', f'//{token}:x-oauth-basic@', from_url)

    to_path = repository_record.filesystem_path
    from_branch = repository_record.branch

    try:
        repo_helper = GitRepo(to_path, from_url)
        head = repo_helper.checkout(from_branch, head)
        repository_record.current_head = head
        # Make sure we don't recursively trigger a new resync of the repository!
        repository_record.save(trigger_resync=False)

    except Exception as exc:
        if job_result:
            job_result.set_status(JobResultStatusChoices.STATUS_ERRORED)
            job_result.log(str(exc), level_choice=LogLevelChoices.LOG_FAILURE, logger=logger)
            job_result.save()
        elif logger:
            logger.error(str(exc))
        raise

    if job_result:
        job_result.log("Repository successfully refreshed", level_choice=LogLevelChoices.LOG_SUCCESS, logger=logger)
        job_result.save()
    elif logger:
        logger.info("Repository successfully refreshed")

#
# Config context handling
#


def refresh_git_config_contexts(repository_record, job_result):
    """Callback function for GitRepository updates - refresh all ConfigContext records managed by this repository."""
    if "extras.ConfigContext" in repository_record.provided_contents:
        update_git_config_contexts(repository_record, job_result)
    else:
        delete_git_config_contexts(repository_record, job_result)


def update_git_config_contexts(repository_record, job_result):
    """Refresh any config contexts provided by this Git repository."""
    config_context_path = os.path.join(repository_record.filesystem_path, "config_contexts")
    if not os.path.isdir(config_context_path):
        return

    managed_config_contexts = set()
    for filename in os.listdir(config_context_path):
        job_result.log(f"Loading config context from `{filename}`", logger=logger)
        context_record = None
        try:
            with open(os.path.join(config_context_path, filename)) as fd:
                # The data file can be either JSON or YAML; since YAML is a superset of JSON, we can load it regardless
                try:
                    context_data = yaml.safe_load(fd)
                except Exception as exc:
                    raise RuntimeError(f"Error in loading config context data from `{filename}`: {exc}")

            # A file can contain one config context dict or a list thereof
            if isinstance(context_data, dict):
                import_config_context(context_data, repository_record, job_result, logger)
                managed_config_contexts.add(context_data.get('name'))
            elif isinstance(context_data, list):
                for context_data_entry in context_data:
                    import_config_context(context_data_entry, repository_record, job_result, logger)
                    managed_config_contexts.add(context_data_entry.get('name'))
            else:
                raise RuntimeError(
                    f"Error in loading config context data from `{filename}`: data must be a dict or list of dicts"
                )

        except Exception as exc:
            job_result.log(str(exc), obj=context_record, level_choice=LogLevelChoices.LOG_FAILURE, logger=logger)
            job_result.save()

    # Delete any prior contexts that are owned by this repository but were not created/updated above
    delete_git_config_contexts(repository_record, job_result, preserve=managed_config_contexts)


def import_config_context(context_data, repository_record, job_result, logger):
    """
    Parse a given dictionary of data to create/update a ConfigContext record.

    Note that we don't use extras.api.serializers.ConfigContextSerializer, despite superficial similarities;
    the reason is that the serializer only allows us to identify related objects (Region, Site, DeviceRole, etc.)
    by their database primary keys, whereas here we need to be able to look them up by other values such as slug.
    """
    git_repository_content_type = ContentType.objects.get_for_model(GitRepository)

    context_record = None
    # TODO: check context_data against a schema of some sort?

    # Set defaults for optional fields
    context_data.setdefault('description', '')
    context_data.setdefault('is_active', True)

    # Translate relationship queries/filters to lists of related objects
    relations = {}
    for key, model_class in [
        ('regions', Region),
        ('sites', Site),
        ('roles', DeviceRole),
        ('platforms', Platform),
        ('cluster_groups', ClusterGroup),
        ('clusters', Cluster),
        ('tenant_groups', TenantGroup),
        ('tenants', Tenant),
        ('tags', Tag),
    ]:
        relations[key] = []
        for object_data in context_data.get(key, ()):
            try:
                object_instance = model_class.objects.get(**object_data)
            except model_class.DoesNotExist as exc:
                raise RuntimeError(
                    f"No matching {model_class.__name__} found for {object_data}; unable to create/update "
                    f"context {context_data.get('name')}"
                ) from exc
            except model_class.MultipleObjectsReturned as exc:
                raise RuntimeError(
                    f"Multiple {model_class.__name__} found for {object_data}; unable to create/update "
                    f"context {context_data.get('name')}"
                ) from exc
            relations[key].append(object_instance)

    with transaction.atomic():
        # FIXME: Normally ObjectChange records are automatically generated every time we save an object,
        # regardless of whether any fields were actually modified.
        # Because a single GitRepository may manage dozens of records, this would result in a lot of noise
        # every time a repository gets resynced.
        # To reduce that noise until the base issue is fixed, we need to explicitly detect object changes:
        created = False
        modified = False
        save_needed = False
        try:
            context_record = ConfigContext.objects.get(
                name=context_data.get('name'),
                owner_content_type=git_repository_content_type,
                owner_object_id=repository_record.pk,
            )
        except ConfigContext.DoesNotExist:
            context_record = ConfigContext(
                name=context_data.get('name'),
                owner_content_type=git_repository_content_type,
                owner_object_id=repository_record.pk,
            )
            created = True

        for field in ('weight', 'description', 'is_active', 'data'):
            new_value = context_data[field]
            if getattr(context_record, field) != new_value:
                setattr(context_record, field, new_value)
                modified = True
                save_needed = True

        if created:
            # Save it so that it gets a PK, required before we can set the relations
            context_record.save()
            save_needed = False

        for key, objects in relations.items():
            field = getattr(context_record, key)
            value = list(field.all())
            if value != objects:
                field.set(objects)
                # Calling set() on a ManyToManyField doesn't require a subsequent save() call
                modified = True

        if save_needed:
            context_record.save()

    if created:
        job_result.log(
            "Successfully created config context",
            obj=context_record,
            level_choice=LogLevelChoices.LOG_SUCCESS,
            logger=logger
        )
    elif modified:
        job_result.log(
            "Successfully refreshed config context",
            obj=context_record,
            level_choice=LogLevelChoices.LOG_SUCCESS,
            logger=logger
        )
    else:
        job_result.log(
            "No change to config context",
            obj=context_record,
            level_choice=LogLevelChoices.LOG_INFO,
            logger=logger
        )


def delete_git_config_contexts(repository_record, job_result, preserve=()):
    """Delete config contexts owned by this Git repository that are not in the preserve list (if any)."""
    git_repository_content_type = ContentType.objects.get_for_model(GitRepository)
    for context_record in ConfigContext.objects.filter(
        owner_content_type=git_repository_content_type, owner_object_id=repository_record.pk
    ):
        if context_record.name not in preserve:
            context_record.delete()
            job_result.log(
                f"Deleted config context {context_record}", level_choice=LogLevelChoices.LOG_WARNING, logger=logger
            )

#
# Custom job handling
#


def refresh_git_custom_jobs(repository_record, job_result):
    """Callback function for GitRepository updates - refresh all CustomJob records managed by this repository."""
    # No-op as custom jobs are not currently stored in the DB but are instead refreshed on-request.

#
# Export template handling
#


def refresh_git_export_templates(repository_record, job_result):
    """Callback function for GitRepository updates - refresh all ExportTemplate records managed by this repository."""
    if "extras.ExportTemplate" in repository_record.provided_contents:
        update_git_export_templates(repository_record, job_result)
    else:
        delete_git_export_templates(repository_record, job_result)


def update_git_export_templates(repository_record, job_result):
    """Refresh any export templates provided by this Git repository.

    Templates are located in GIT_ROOT/<repo>/export_templates/<app_label>/<model>/<template name>.
    """
    export_template_path = os.path.join(repository_record.filesystem_path, "export_templates")
    if not os.path.isdir(export_template_path):
        return

    git_repository_content_type = ContentType.objects.get_for_model(GitRepository)

    managed_export_templates = {}
    for app_label in os.listdir(export_template_path):
        app_label_path = os.path.join(export_template_path, app_label)
        if not os.path.isdir(app_label_path):
            continue
        for modelname in os.listdir(app_label_path):
            model_path = os.path.join(app_label_path, modelname)
            if not os.path.isdir(model_path):
                continue

            try:
                model_content_type = ContentType.objects.get(app_label=app_label, model=modelname)
            except ContentType.DoesNotExist:
                job_result.log(
                    f"Skipping `{app_label}.{modelname}` as it isn't a known content type",
                    level_choice=LogLevelChoices.LOG_FAILURE,
                    logger=logger,
                )
                continue

            for filename in os.listdir(model_path):
                job_result.log(f"Loading `{app_label}.{modelname}` export template from `{filename}`", logger=logger)
                managed_export_templates.setdefault(f"{app_label}.{modelname}", set()).add(filename)
                template_record = None
                try:
                    with open(os.path.join(model_path, filename), 'r') as fd:
                        template_content = fd.read()

                    # FIXME: Normally ObjectChange records are automatically generated every time we save an object,
                    # regardless of whether any fields were actually modified.
                    # Because a single GitRepository may manage dozens of records, this would result in a lot
                    # of noise every time a repository gets resynced.
                    # To reduce noise until the base issue is fixed, we need to explicitly detect object changes:
                    created = False
                    modified = False
                    try:
                        template_record = ExportTemplate.objects.get(
                            content_type=model_content_type,
                            name=filename,
                            owner_content_type=git_repository_content_type,
                            owner_object_id=repository_record.pk,
                        )
                    except ExportTemplate.DoesNotExist:
                        template_record = ExportTemplate(
                            content_type=model_content_type,
                            name=filename,
                            owner_content_type=git_repository_content_type,
                            owner_object_id=repository_record.pk,
                        )
                        created = True
                        modified = True

                    if template_record.template_code != template_content:
                        template_record.template_code = template_content
                        modified = True

                    if template_record.mime_type != 'text/plain':
                        template_record.mime_type = 'text/plain'
                        modified = True

                    if template_record.file_extension != os.path.splitext(filename)[-1]:
                        template_record.file_extension = os.path.splitext(filename)[-1]
                        modified = True

                    if modified:
                        template_record.save()

                    if created:
                        job_result.log(
                            "Successfully created export template",
                            obj=template_record,
                            level_choice=LogLevelChoices.LOG_SUCCESS,
                            logger=logger
                        )
                    elif modified:
                        job_result.log(
                            "Successfully refreshed export template",
                            obj=template_record,
                            level_choice=LogLevelChoices.LOG_SUCCESS,
                            logger=logger
                        )
                    else:
                        job_result.log(
                            "No change to export template",
                            obj=template_record,
                            level_choice=LogLevelChoices.LOG_INFO,
                            logger=logger,
                        )

                except Exception as exc:
                    job_result.log(
                        str(exc), obj=template_record, level_choice=LogLevelChoices.LOG_FAILURE, logger=logger,
                    )
                    job_result.save()

    # Delete any prior templates that are owned by this repository but were not discovered above
    delete_git_export_templates(repository_record, job_result, preserve=managed_export_templates)


def delete_git_export_templates(repository_record, job_result, preserve=None):
    """Delete ExportTemplates owned by the given Git repository that are not in the preserve dict (if any)."""
    git_repository_content_type = ContentType.objects.get_for_model(GitRepository)
    if not preserve:
        preserve = {}

    for template_record in ExportTemplate.objects.filter(
        owner_content_type=git_repository_content_type, owner_object_id=repository_record.pk
    ):
        key = f"{template_record.content_type.app_label}.{template_record.content_type.name}"
        if template_record.name not in preserve.get(key, ()):
            template_record.delete()
            job_result.log(
                f"Deleted export template {template_record}", level_choice=LogLevelChoices.LOG_WARNING, logger=logger
            )


# Register built-in callbacks for data types potentially provided by a GitRepository
register_datasource_contents(
    [
        (
            'extras.GitRepository',
            DatasourceContent(
                name='config contexts',
                token='extras.ConfigContext',
                icon='mdi-code-json',
                callback=refresh_git_config_contexts,
            ),
        ),
        (
            'extras.GitRepository',
            DatasourceContent(
                name='custom jobs',
                token='extras.CustomJob',
                icon='mdi-script-text',
                callback=refresh_git_custom_jobs,
            ),
        ),
        (
            'extras.GitRepository',
            DatasourceContent(
                name='export templates',
                token='extras.ExportTemplate',
                icon='mdi-database-export',
                callback=refresh_git_export_templates,
            ),
        ),
    ]
)
