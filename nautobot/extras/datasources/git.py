"""Git data source functionality."""

from collections import defaultdict
import logging
import os
import re
from urllib.parse import quote

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.utils.text import slugify
from django_rq import job
import yaml

from nautobot.dcim.models import Device, DeviceRole, Platform, Region, Site
from nautobot.extras.choices import LogLevelChoices, JobResultStatusChoices
from nautobot.extras.models import (
    ConfigContext,
    ConfigContextSchema,
    ExportTemplate,
    GitRepository,
    JobResult,
    Tag,
)
from nautobot.extras.registry import DatasourceContent, register_datasource_contents
from nautobot.tenancy.models import TenantGroup, Tenant
from nautobot.utilities.git import GitRepo
from nautobot.utilities.utils import copy_safe_request
from nautobot.virtualization.models import ClusterGroup, Cluster, VirtualMachine
from .registry import refresh_datasource_content
from .utils import files_from_contenttype_directories


logger = logging.getLogger("nautobot.datasources.git")


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


@job("default")
def pull_git_repository_and_refresh_data(repository_pk, request, job_result):
    """
    Worker function to clone and/or pull a Git repository into Nautobot, then invoke refresh_datasource_content().
    """
    repository_record = GitRepository.objects.get(pk=repository_pk)
    if not repository_record:
        job_result.log(
            f"No GitRepository {repository_pk} found!",
            level_choice=LogLevelChoices.LOG_FAILURE,
            logger=logger,
        )
        job_result.set_status(JobResultStatusChoices.STATUS_ERRORED)
        job_result.save()
        return

    job_result.log(
        f'Creating/refreshing local copy of Git repository "{repository_record.name}"...',
        logger=logger,
    )
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

        refresh_datasource_content("extras.gitrepository", repository_record, request, job_result, delete=False)

    except Exception as exc:
        job_result.log(
            f"Error while refreshing {repository_record.name}: {exc}",
            level_choice=LogLevelChoices.LOG_FAILURE,
        )
        job_result.set_status(JobResultStatusChoices.STATUS_ERRORED)

    finally:
        if job_result.status not in JobResultStatusChoices.TERMINAL_STATE_CHOICES:
            if job_result.data["total"][LogLevelChoices.LOG_FAILURE] > 0:
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
    such as to ensure that different Nautobot instances and/or worker instances all have a local copy of the same HEAD.

    Args:
      repository_record (GitRepository)
      job_result (JobResult): Optional JobResult to store results into.
      logger (logging.Logger): Optional Logger to additionally log results to.
      head (str): Optional Git commit hash to check out instead of pulling branch latest.
    """

    # Inject token into source URL if necessary
    from_url = repository_record.remote_url
    token = repository_record._token
    user = repository_record.username
    if token and token not in from_url:
        # Some git repositories require a user as well as a token.
        if user:
            from_url = re.sub("//", f"//{quote(user, safe='')}:{quote(token, safe='')}@", from_url)
        else:
            from_url = re.sub("//", f"//{quote(token, safe='')}@", from_url)

    to_path = repository_record.filesystem_path
    from_branch = repository_record.branch

    try:
        repo_helper = GitRepo(to_path, from_url)
        head = repo_helper.checkout(from_branch, head)
        if repository_record.current_head != head:
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
        job_result.log(
            "Repository successfully refreshed",
            level_choice=LogLevelChoices.LOG_SUCCESS,
            logger=logger,
        )
        job_result.save()
    elif logger:
        logger.info("Repository successfully refreshed")


#
# Config context handling
#


def refresh_git_config_contexts(repository_record, job_result, delete=False):
    """Callback function for GitRepository updates - refresh all ConfigContext records managed by this repository."""
    if "extras.configcontext" in repository_record.provided_contents and not delete:
        update_git_config_contexts(repository_record, job_result)
    else:
        delete_git_config_contexts(repository_record, job_result)


def update_git_config_contexts(repository_record, job_result):
    """Refresh any config contexts provided by this Git repository."""
    config_context_path = os.path.join(repository_record.filesystem_path, "config_contexts")
    if not os.path.isdir(config_context_path):
        return

    managed_config_contexts = set()
    managed_local_config_contexts = defaultdict(set)

    # First, handle the "flat file" case - data files in the root config_context_path,
    # whose metadata is expressed purely within the contents of the file:
    for file_name in os.listdir(config_context_path):
        if not os.path.isfile(os.path.join(config_context_path, file_name)):
            continue
        job_result.log(
            f"Loading config context from `{file_name}`",
            grouping="config contexts",
            logger=logger,
        )
        try:
            with open(os.path.join(config_context_path, file_name), "r") as fd:
                # The data file can be either JSON or YAML; since YAML is a superset of JSON, we can load it regardless
                try:
                    context_data = yaml.safe_load(fd)
                except Exception as exc:
                    raise RuntimeError(f"Error in loading config context data from `{file_name}`: {exc}")

            # A file can contain one config context dict or a list thereof
            if isinstance(context_data, dict):
                context_name = import_config_context(context_data, repository_record, job_result, logger)
                managed_config_contexts.add(context_name)
            elif isinstance(context_data, list):
                for context_data_entry in context_data:
                    context_name = import_config_context(context_data_entry, repository_record, job_result, logger)
                    managed_config_contexts.add(context_name)
            else:
                raise RuntimeError(
                    f"Error in loading config context data from `{file_name}`: data must be a dict or list of dicts"
                )

        except Exception as exc:
            job_result.log(
                str(exc),
                level_choice=LogLevelChoices.LOG_FAILURE,
                grouping="config contexts",
                logger=logger,
            )
            job_result.save()

    # Next, handle the "filter/slug directory structure case - files in <filter_type>/<slug>.(json|yaml)
    for filter_type in (
        "regions",
        "sites",
        "roles",
        "platforms",
        "cluster_groups",
        "clusters",
        "tenant_groups",
        "tenants",
        "tags",
    ):
        dir_path = os.path.join(config_context_path, filter_type)
        if not os.path.isdir(dir_path):
            continue

        for file_name in os.listdir(dir_path):
            slug = os.path.splitext(file_name)[0]
            job_result.log(
                f'Loading config context, filter `{filter_type} = [slug: "{slug}"]`, from `{filter_type}/{file_name}`',
                grouping="config contexts",
                logger=logger,
            )
            try:
                with open(os.path.join(dir_path, file_name), "r") as fd:
                    # Data file can be either JSON or YAML; since YAML is a superset of JSON, we can load it regardless
                    try:
                        context_data = yaml.safe_load(fd)
                    except Exception as exc:
                        raise RuntimeError(f"Error in loading config context data from `{file_name}`: {exc}")

                # Unlike the above case, these files always contain just a single config context record

                # Add the implied filter to the context metadata
                context_data.setdefault("_metadata", {}).setdefault(filter_type, []).append({"slug": slug})

                context_name = import_config_context(context_data, repository_record, job_result, logger)
                managed_config_contexts.add(context_name)
            except Exception as exc:
                job_result.log(
                    str(exc),
                    level_choice=LogLevelChoices.LOG_FAILURE,
                    grouping="config contexts",
                    logger=logger,
                )
                job_result.save()

    # Finally, handle device- and virtual-machine-specific "local" context in (devices|virtual_machines)/<name>.(json|yaml)
    for local_type in ("devices", "virtual_machines"):
        dir_path = os.path.join(config_context_path, local_type)
        if not os.path.isdir(dir_path):
            continue

        for file_name in os.listdir(dir_path):
            device_name = os.path.splitext(file_name)[0]
            job_result.log(
                f"Loading local config context for `{device_name}` from `{local_type}/{file_name}`",
                grouping="local config contexts",
                logger=logger,
            )
            try:
                with open(os.path.join(dir_path, file_name), "r") as fd:
                    try:
                        context_data = yaml.safe_load(fd)
                    except Exception as exc:
                        raise RuntimeError(f"Error in loading local config context from `{file_name}`: {exc}")

                import_local_config_context(
                    local_type,
                    device_name,
                    context_data,
                    repository_record,
                    job_result,
                    logger,
                )
                managed_local_config_contexts[local_type].add(device_name)
            except Exception as exc:
                job_result.log(
                    str(exc),
                    level_choice=LogLevelChoices.LOG_FAILURE,
                    grouping="local config contexts",
                    logger=logger,
                )
                job_result.save()

    # Delete any prior contexts that are owned by this repository but were not created/updated above
    delete_git_config_contexts(
        repository_record,
        job_result,
        preserve=managed_config_contexts,
        preserve_local=managed_local_config_contexts,
    )


def import_config_context(context_data, repository_record, job_result, logger):
    """
    Parse a given dictionary of data to create/update a ConfigContext record.

    The dictionary is expected to have a key "_metadata" which defines properties on the ConfigContext record itself
    (name, weight, description, etc.), while all other keys in the dictionary will go into the record's "data" field.

    Note that we don't use extras.api.serializers.ConfigContextSerializer, despite superficial similarities;
    the reason is that the serializer only allows us to identify related objects (Region, Site, DeviceRole, etc.)
    by their database primary keys, whereas here we need to be able to look them up by other values such as slug.
    """
    git_repository_content_type = ContentType.objects.get_for_model(GitRepository)

    context_record = None
    # TODO: check context_data against a schema of some sort?

    # Set defaults for optional fields
    context_metadata = context_data.setdefault("_metadata", {})
    context_metadata.setdefault("weight", 1000)
    context_metadata.setdefault("description", "")
    context_metadata.setdefault("is_active", True)

    # Translate relationship queries/filters to lists of related objects
    relations = {}
    for key, model_class in [
        ("regions", Region),
        ("sites", Site),
        ("roles", DeviceRole),
        ("platforms", Platform),
        ("cluster_groups", ClusterGroup),
        ("clusters", Cluster),
        ("tenant_groups", TenantGroup),
        ("tenants", Tenant),
        ("tags", Tag),
    ]:
        relations[key] = []
        for object_data in context_metadata.get(key, ()):
            try:
                object_instance = model_class.objects.get(**object_data)
            except model_class.DoesNotExist as exc:
                raise RuntimeError(
                    f"No matching {model_class.__name__} found for {object_data}; unable to create/update "
                    f"context {context_metadata.get('name')}"
                ) from exc
            except model_class.MultipleObjectsReturned as exc:
                raise RuntimeError(
                    f"Multiple {model_class.__name__} found for {object_data}; unable to create/update "
                    f"context {context_metadata.get('name')}"
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
                name=context_metadata.get("name"),
                owner_content_type=git_repository_content_type,
                owner_object_id=repository_record.pk,
            )
        except ConfigContext.DoesNotExist:
            context_record = ConfigContext(
                name=context_metadata.get("name"),
                owner_content_type=git_repository_content_type,
                owner_object_id=repository_record.pk,
            )
            created = True

        for field in ("weight", "description", "is_active"):
            new_value = context_metadata[field]
            if getattr(context_record, field) != new_value:
                setattr(context_record, field, new_value)
                modified = True
                save_needed = True

        data = context_data.copy()
        del data["_metadata"]

        if context_metadata["schema"]:
            if getattr(context_record, "name", None) != context_metadata["schema"]:
                try:
                    schema = ConfigContextSchema.objects.get(name=context_metadata["schema"])
                    context_record.schema = schema
                except ConfigContextSchema.DoesNotExist:
                    job_result.log(
                        f"ConfigContextSchema {context_metadata['schema']} does not exist.",
                        obj=context_record,
                        level_choice=LogLevelChoices.LOG_FAILURE,
                        grouping="config contexts",
                        logger=logger,
                    )


        if context_record.data != data:
            context_record.data = data
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
            grouping="config contexts",
            logger=logger,
        )
    elif modified:
        job_result.log(
            "Successfully refreshed config context",
            obj=context_record,
            level_choice=LogLevelChoices.LOG_SUCCESS,
            grouping="config contexts",
            logger=logger,
        )
    else:
        job_result.log(
            "No change to config context",
            obj=context_record,
            level_choice=LogLevelChoices.LOG_INFO,
            grouping="config contexts",
            logger=logger,
        )

    return context_record.name if context_record else None


def import_local_config_context(local_type, device_name, context_data, repository_record, job_result, logger):
    """
    Create/update the local config context data associated with a Device or VirtualMachine.
    """
    try:
        if local_type == "devices":
            record = Device.objects.get(name=device_name)
        elif local_type == "virtual_machines":
            record = VirtualMachine.objects.get(name=device_name)
    except MultipleObjectsReturned:
        # Possible for Device as name is not guaranteed globally unique
        # TODO: come up with a design that accounts for non-unique names, as well as un-named Devices.
        job_result.log(
            "Multiple records with the same name found; unable to determine which one to apply to!",
            level_choice=LogLevelChoices.LOG_FAILURE,
            grouping="local config contexts",
            logger=logger,
        )
        return
    except ObjectDoesNotExist:
        job_result.log(
            "Record not found!",
            level_choice=LogLevelChoices.LOG_FAILURE,
            grouping="local config contexts",
            logger=logger,
        )
        return

    if record.local_context_data_owner is not None and record.local_context_data_owner != repository_record:
        job_result.log(
            f"DATA CONFLICT: Local context data is owned by another owner, {record.local_context_data_owner}",
            obj=record,
            level_choice=LogLevelChoices.LOG_FAILURE,
            grouping="local config contexts",
            logger=logger,
        )
        return

    if record.local_context_data == context_data and record.local_context_data_owner == repository_record:
        job_result.log(
            "No change to local config context",
            obj=record,
            level_choice=LogLevelChoices.LOG_INFO,
            grouping="local config contexts",
            logger=logger,
        )
        return

    record.local_context_data = context_data
    record.local_context_data_owner = repository_record
    record.clean()
    record.save()
    job_result.log(
        "Successfully updated local config context",
        obj=record,
        level_choice=LogLevelChoices.LOG_SUCCESS,
        grouping="local config contexts",
        logger=logger,
    )


def delete_git_config_contexts(repository_record, job_result, preserve=(), preserve_local=None):
    """Delete config contexts owned by this Git repository that are not in the preserve list (if any)."""
    if not preserve_local:
        preserve_local = defaultdict(set)

    git_repository_content_type = ContentType.objects.get_for_model(GitRepository)
    for context_record in ConfigContext.objects.filter(
        owner_content_type=git_repository_content_type,
        owner_object_id=repository_record.pk,
    ):
        if context_record.name not in preserve:
            context_record.delete()
            job_result.log(
                f"Deleted config context {context_record}",
                level_choice=LogLevelChoices.LOG_WARNING,
                grouping="config contexts",
                logger=logger,
            )

    for grouping, model in (
        ("devices", Device),
        ("virtual_machines", VirtualMachine),
    ):
        for record in model.objects.filter(
            local_context_data_owner_content_type=git_repository_content_type,
            local_context_data_owner_object_id=repository_record.pk,
        ):
            if record.name not in preserve_local[grouping]:
                record.local_context_data = None
                record.local_context_data_owner = None
                record.clean()
                record.save()
                job_result.log(
                    "Deleted local config context",
                    obj=record,
                    level_choice=LogLevelChoices.LOG_WARNING,
                    grouping="local config contexts",
                    logger=logger,
                )


#
# Config Context Schemas
#


def refresh_git_config_context_schemas(repository_record, job_result, delete=False):
    """Callback function for GitRepository updates - refresh all ConfigContextSchema records managed by this repository."""
    if "extras.configcontextschema" in repository_record.provided_contents and not delete:
        update_git_config_context_schemas(repository_record, job_result)
    else:
        delete_git_config_context_schemas(repository_record, job_result)


def update_git_config_context_schemas(repository_record, job_result):
    """Refresh any config context schemas provided by this Git repository."""
    config_context_path = os.path.join(repository_record.filesystem_path, "config_context_schemas")
    if not os.path.isdir(config_context_path):
        return

    managed_config_context_schemas = set()

    for file_name in os.listdir(config_context_path):
        if not os.path.isfile(os.path.join(config_context_path, file_name)):
            continue
        job_result.log(
            f"Loading config context schema from `{file_name}`",
            grouping="config contexts",
            logger=logger,
        )
        try:
            with open(os.path.join(config_context_path, file_name), "r") as fd:
                # The data file can be either JSON or YAML; since YAML is a superset of JSON, we can load it regardless
                try:
                    context_schema_data = yaml.safe_load(fd)
                except Exception as exc:
                    raise RuntimeError(f"Error in loading config context schema data from `{file_name}`: {exc}")

            # A file can contain one config context dict or a list thereof
            if isinstance(context_schema_data, dict):
                context_name = import_config_context_schema(context_schema_data, repository_record, job_result, logger)
                managed_config_context_schemas.add(context_name)
            elif isinstance(context_schema_data, list):
                for context_schema in context_schema_data:
                    context_name = import_config_context_schema(context_schema, repository_record, job_result, logger)
                    managed_config_context_schemas.add(context_name)
            else:
                raise RuntimeError(
                    f"Error in loading config context schema data from `{file_name}`: data must be a dict or list of dicts"
                )
        except Exception as exc:
            job_result.log(
                str(exc),
                level_choice=LogLevelChoices.LOG_FAILURE,
                grouping="config context schemas",
                logger=logger,
            )
            job_result.save()

    # Delete any prior contexts that are owned by this repository but were not created/updated above
    delete_git_config_context_schemas(
        repository_record,
        job_result,
        preserve=managed_config_context_schemas,
    )


def import_config_context_schema(context_schema_data, repository_record, job_result, logger):
    """Using data from schema file, create schema record in Nautobot."""
    git_repository_content_type = ContentType.objects.get_for_model(GitRepository)

    created = False
    modified = False

    schema_metadata = context_schema_data.setdefault("_metadata", {})

    if not schema_metadata.get("name"):
        raise RuntimeError("File has no name set.")

    try:
        schema_record = ConfigContextSchema.objects.get(
            name=schema_metadata["name"],
            owner_content_type=git_repository_content_type,
            owner_object_id=repository_record.pk,
        )
    except ConfigContextSchema.DoesNotExist:
        schema_record = ConfigContextSchema(
            name=schema_metadata["name"],
            slug=slugify(schema_metadata["name"]),
            owner_content_type=git_repository_content_type,
            owner_object_id=repository_record.pk,
            data_schema=context_schema_data["data_schema"],
        )
        created = True

    if schema_record.description != schema_metadata.get("description", ""):
        schema_record.description = schema_metadata.get("description", "")
        modified = True

    if schema_record.data_schema != context_schema_data["data_schema"]:
        schema_record.data_schema = context_schema_data["data_schema"]
        modified = True

    if created:
        schema_record.validated_save()
        job_result.log(
            "Successfully created config context schema",
            obj=schema_record,
            level_choice=LogLevelChoices.LOG_SUCCESS,
            grouping="config context schemas",
            logger=logger,
        )
    elif modified:
        schema_record.validated_save()
        job_result.log(
            "Successfully refreshed config context schema",
            obj=schema_record,
            level_choice=LogLevelChoices.LOG_SUCCESS,
            grouping="config context schemas",
            logger=logger,
        )
    else:
        job_result.log(
            "No change to config context schema",
            obj=schema_record,
            level_choice=LogLevelChoices.LOG_INFO,
            grouping="config context schemas",
            logger=logger,
        )

    return schema_record.name if schema_record else None


def delete_git_config_context_schemas(repository_record, job_result, preserve=()):
    """Delete config context schemas owned by this Git repository that are not in the preserve list (if any)."""
    git_repository_content_type = ContentType.objects.get_for_model(GitRepository)
    for schema_record in ConfigContextSchema.objects.filter(
        owner_content_type=git_repository_content_type,
        owner_object_id=repository_record.pk,
    ):
        if schema_record.name not in preserve:
            schema_record.delete()
            job_result.log(
                f"Deleted config context schema {schema_record}",
                level_choice=LogLevelChoices.LOG_WARNING,
                grouping="config context schemas",
                logger=logger,
            )


#
# Job handling
#


def refresh_git_jobs(repository_record, job_result, delete=False):
    """Callback function for GitRepository updates - refresh all Job records managed by this repository."""
    # No-op as jobs are not currently stored in the DB but are instead refreshed on-request.


#
# Export template handling
#


def refresh_git_export_templates(repository_record, job_result, delete=False):
    """Callback function for GitRepository updates - refresh all ExportTemplate records managed by this repository."""
    if "extras.exporttemplate" in repository_record.provided_contents and not delete:
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
    for model_content_type, file_path in files_from_contenttype_directories(
        export_template_path, job_result, "export templates"
    ):
        file_name = os.path.basename(file_path)
        app_label = model_content_type.app_label
        modelname = model_content_type.model
        job_result.log(
            f"Loading `{app_label}.{modelname}` export template from `{file_name}`",
            grouping="export templates",
            logger=logger,
        )
        managed_export_templates.setdefault(f"{app_label}.{modelname}", set()).add(file_name)
        template_record = None
        try:
            with open(file_path, "r") as fd:
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
                    name=file_name,
                    owner_content_type=git_repository_content_type,
                    owner_object_id=repository_record.pk,
                )
            except ExportTemplate.DoesNotExist:
                template_record = ExportTemplate(
                    content_type=model_content_type,
                    name=file_name,
                    owner_content_type=git_repository_content_type,
                    owner_object_id=repository_record.pk,
                )
                created = True
                modified = True

            if template_record.template_code != template_content:
                template_record.template_code = template_content
                modified = True

            if template_record.mime_type != "text/plain":
                template_record.mime_type = "text/plain"
                modified = True

            if template_record.file_extension != file_name.rsplit(os.extsep, 1)[-1]:
                template_record.file_extension = file_name.rsplit(os.extsep, 1)[-1]
                modified = True

            if modified:
                template_record.save()

            if created:
                job_result.log(
                    "Successfully created export template",
                    obj=template_record,
                    level_choice=LogLevelChoices.LOG_SUCCESS,
                    grouping="export templates",
                    logger=logger,
                )
            elif modified:
                job_result.log(
                    "Successfully refreshed export template",
                    obj=template_record,
                    level_choice=LogLevelChoices.LOG_SUCCESS,
                    grouping="export templates",
                    logger=logger,
                )
            else:
                job_result.log(
                    "No change to export template",
                    obj=template_record,
                    level_choice=LogLevelChoices.LOG_INFO,
                    grouping="export templates",
                    logger=logger,
                )

        except Exception as exc:
            job_result.log(
                str(exc),
                obj=template_record,
                level_choice=LogLevelChoices.LOG_FAILURE,
                grouping="export templates",
                logger=logger,
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
        owner_content_type=git_repository_content_type,
        owner_object_id=repository_record.pk,
    ):
        key = f"{template_record.content_type.app_label}.{template_record.content_type.name}"
        if template_record.name not in preserve.get(key, ()):
            template_record.delete()
            job_result.log(
                f"Deleted export template {template_record}",
                level_choice=LogLevelChoices.LOG_WARNING,
                grouping="export templates",
                logger=logger,
            )


# Register built-in callbacks for data types potentially provided by a GitRepository
register_datasource_contents(
    [
        (
            "extras.gitrepository",
            DatasourceContent(
                name="config context schemas",
                content_identifier="extras.configcontextschema",
                icon="mdi-floor-plan",
                weight=100,
                callback=refresh_git_config_context_schemas,
            ),
        ),
        (
            "extras.gitrepository",
            DatasourceContent(
                name="config contexts",
                content_identifier="extras.configcontext",
                icon="mdi-code-json",
                weight=200,
                callback=refresh_git_config_contexts,
            ),
        ),
        (
            "extras.gitrepository",
            DatasourceContent(
                name="jobs",
                content_identifier="extras.job",
                icon="mdi-script-text",
                weight=300,
                callback=refresh_git_jobs,
            ),
        ),
        (
            "extras.gitrepository",
            DatasourceContent(
                name="export templates",
                content_identifier="extras.exporttemplate",
                icon="mdi-database-export",
                weight=400,
                callback=refresh_git_export_templates,
            ),
        ),
    ]
)
