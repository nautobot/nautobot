"""Git data source functionality."""

from collections import defaultdict, namedtuple
import logging
import mimetypes
import os
import re
import sys
from urllib.parse import quote

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db import transaction
import yaml

from nautobot.core.celery import app as celery_app
from nautobot.core.utils.git import GitRepo
from nautobot.dcim.models import Device, DeviceType, Location, Platform
from nautobot.extras.choices import (
    LogLevelChoices,
    SecretsGroupAccessTypeChoices,
    SecretsGroupSecretTypeChoices,
)
from nautobot.extras.models import (
    ConfigContext,
    ConfigContextSchema,
    DynamicGroup,
    ExportTemplate,
    GitRepository,
    Job,
    JobResult,
    Role,
    Tag,
)
from nautobot.extras.registry import DatasourceContent, register_datasource_contents
from nautobot.extras.utils import refresh_job_model_from_job_class
from nautobot.tenancy.models import TenantGroup, Tenant
from nautobot.virtualization.models import ClusterGroup, Cluster, VirtualMachine
from .utils import files_from_contenttype_directories


logger = logging.getLogger(__name__)

# namedtuple takes a job_result(JobResult instance) and a repository_record(GitRepository instance).
GitJobResult = namedtuple("GitJobResult", ["job_result", "repository_record"])

# namedtuple takes from_url(remote git repository url), to_path(local path of git repo), from_branch(git branch)
GitRepoInfo = namedtuple("GitRepoInfo", ["from_url", "to_path", "from_branch"])


def enqueue_git_repository_helper(repository, user, job_class, **kwargs):
    """
    Wrapper for JobResult.enqueue_job() to enqueue one of several possible Git repository functions.
    """
    job_model = job_class().job_model

    return JobResult.enqueue_job(job_model, user, repository=repository.pk)


def enqueue_git_repository_diff_origin_and_local(repository, user):
    """Convenience wrapper for JobResult.enqueue_job() to enqueue the git_repository_diff_origin_and_local job."""
    from nautobot.core.jobs import GitRepositoryDryRun

    return enqueue_git_repository_helper(repository, user, GitRepositoryDryRun)


def enqueue_pull_git_repository_and_refresh_data(repository, user):
    """
    Convenience wrapper for JobResult.enqueue_job() to enqueue the pull_git_repository_and_refresh_data job.
    """
    from nautobot.core.jobs import GitRepositorySync

    return enqueue_git_repository_helper(repository, user, GitRepositorySync)


def get_repo_from_url_to_path_and_from_branch(repository_record):
    """Returns the from_url, to_path and from_branch of a Git Repo
    Returns:
        namedtuple (GitRepoInfo): (
        from_url: git repo url with token or user if available,
        to_path: path to location of git repo on local machine
        from_branch: current git repo branch
    )
    """

    # Inject username and/or token into source URL if necessary
    from_url = repository_record.remote_url

    user = None
    token = None
    if repository_record.secrets_group:
        # In addition to ObjectDoesNotExist, get_secret_value() may also raise a SecretError if a secret is mis-defined;
        # we don't catch that here but leave it up to the caller to handle as part of general exception handling.
        try:
            token = repository_record.secrets_group.get_secret_value(
                SecretsGroupAccessTypeChoices.TYPE_HTTP,
                SecretsGroupSecretTypeChoices.TYPE_TOKEN,
                obj=repository_record,
            )
        except ObjectDoesNotExist:
            # No defined secret, fall through to legacy behavior
            pass
        try:
            user = repository_record.secrets_group.get_secret_value(
                SecretsGroupAccessTypeChoices.TYPE_HTTP,
                SecretsGroupSecretTypeChoices.TYPE_USERNAME,
                obj=repository_record,
            )
        except ObjectDoesNotExist:
            # No defined secret, fall through to legacy behavior
            pass

    if token and token not in from_url:
        # Some git repositories require a user as well as a token.
        if user:
            from_url = re.sub("//", f"//{quote(user, safe='')}:{quote(token, safe='')}@", from_url)
        else:
            from_url = re.sub("//", f"//{quote(token, safe='')}@", from_url)

    to_path = repository_record.filesystem_path
    from_branch = repository_record.branch

    return GitRepoInfo(from_url=from_url, to_path=to_path, from_branch=from_branch)


def ensure_git_repository(repository_record, logger=None, head=None):  # pylint: disable=redefined-outer-name
    """Ensure that the given Git repo is present, up-to-date, and has the correct branch selected.
    Note that this function may be called independently of the `GitRepositoryiSync` job,
    such as to ensure that different Nautobot instances and/or worker instances all have a local copy of the same HEAD.
    Args:
      repository_record (GitRepository): Repository to ensure the state of.
      logger (logging.Logger): Optional Logger to log results to.
      head (str): Optional Git commit hash to check out instead of pulling branch latest.

    Returns:
      bool: Whether any change to the local repo actually occurred.
    """

    from_url, to_path, from_branch = get_repo_from_url_to_path_and_from_branch(repository_record)

    try:
        repo_helper = GitRepo(to_path, from_url)
        head, changed = repo_helper.checkout(from_branch, head)
        if repository_record.current_head != head:
            repository_record.current_head = head
            repository_record.save()

    # FIXME(jathan): As a part of jobs overhaul, this error-handling should be removed since this
    # should only ever be called in the context of a Git sync job. Also, all logging directly from a
    # JobResult should also be replaced with just trusting the logger to do the correct thing (such
    # as from the Job class).
    except Exception as exc:
        if logger:
            logger.error(str(exc))
        raise

    if logger:
        if changed:
            logger.info("Repository successfully refreshed")
        logger.info(f'The current Git repository hash is "{repository_record.current_head}"')

    return changed


def git_repository_dry_run(repository_record, logger):  # pylint: disable=redefined-outer-name
    """Log the difference between local branch and remote branch files.
    Args:
        repository_record (GitRepository)
        logger (logging.Logger): Logger to log results to.
    """
    from_url, to_path, from_branch = get_repo_from_url_to_path_and_from_branch(repository_record)

    try:
        repo_helper = GitRepo(to_path, from_url, clone_initially=False)
        logger.info("Fetching from origin")
        modified_files = repo_helper.diff_remote(from_branch)
        if modified_files:
            # Log each modified files
            for item in modified_files:
                logger.info("%s - `%s`", item.status, item.text)
        else:
            logger.info("Repository has no changes")

    except Exception as exc:
        logger.error(str(exc))
        raise

    logger.info("Repository dry run successful")


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
        msg = f"Loading config context from `{file_name}`"
        logger.info(msg)
        job_result.log(msg, grouping="config contexts")
        try:
            with open(os.path.join(config_context_path, file_name), "r") as fd:
                # The data file can be either JSON or YAML; since YAML is a superset of JSON, we can load it regardless
                context_data = yaml.safe_load(fd)

            # A file can contain one config context dict or a list thereof
            if isinstance(context_data, dict):
                context_name = import_config_context(context_data, repository_record, job_result)
                managed_config_contexts.add(context_name)
            elif isinstance(context_data, list):
                for context_data_entry in context_data:
                    context_name = import_config_context(context_data_entry, repository_record, job_result)
                    managed_config_contexts.add(context_name)
            else:
                raise RuntimeError("data must be a dict or list of dicts")

        except Exception as exc:
            msg = f"Error in loading config context data from `{file_name}`: {exc}"
            logger.error(msg)
            job_result.log(msg, level_choice=LogLevelChoices.LOG_ERROR, grouping="config contexts")

    # Next, handle the "filter/name" directory structure case - files in <filter_type>/<name>.(json|yaml)
    for filter_type in (
        "locations",
        "device_types",
        "roles",
        "platforms",
        "cluster_groups",
        "clusters",
        "tenant_groups",
        "tenants",
        "tags",
        "dynamic_groups",
    ):
        if os.path.isdir(os.path.join(repository_record.filesystem_path, filter_type)):
            msg = (
                f'Found "{filter_type}" directory in the repository root. If this is meant to contain config contexts, '
                "it should be moved into a `config_contexts/` subdirectory."
            )
            logger.warning(msg)
            job_result.log(msg, level_choice=LogLevelChoices.LOG_WARNING, grouping="config contexts")

        dir_path = os.path.join(config_context_path, filter_type)
        if not os.path.isdir(dir_path):
            continue

        for file_name in os.listdir(dir_path):
            name = os.path.splitext(file_name)[0]
            msg = f'Loading config context, filter `{filter_type} = [name: "{name}"]`, from `{filter_type}/{file_name}`'
            logger.info(msg)
            job_result.log(msg, grouping="config contexts")
            try:
                with open(os.path.join(dir_path, file_name), "r") as fd:
                    # Data file can be either JSON or YAML; since YAML is a superset of JSON, we can load it regardless
                    context_data = yaml.safe_load(fd)

                # Unlike the above case, these files always contain just a single config context record

                # Add the implied filter to the context metadata
                if filter_type == "device_types":
                    context_data.setdefault("_metadata", {}).setdefault(filter_type, []).append({"model": name})
                else:
                    context_data.setdefault("_metadata", {}).setdefault(filter_type, []).append({"name": name})

                context_name = import_config_context(context_data, repository_record, job_result)
                managed_config_contexts.add(context_name)
            except Exception as exc:
                msg = f"Error in loading config context data from `{file_name}`: {exc}"
                logger.error(msg)
                job_result.log(msg, level_choice=LogLevelChoices.LOG_ERROR, grouping="config contexts")

    # Finally, handle device- and virtual-machine-specific "local" context in (devices|virtual_machines)/<name>.(json|yaml)
    for local_type in ("devices", "virtual_machines"):
        if os.path.isdir(os.path.join(repository_record.filesystem_path, local_type)):
            msg = (
                f'Found "{local_type}" directory in the repository root. If this is meant to contain config contexts, '
                "it should be moved into a `config_contexts/` subdirectory."
            )
            logger.warning(msg)
            job_result.log(msg, level_choice=LogLevelChoices.LOG_WARNING, grouping="config contexts")

        dir_path = os.path.join(config_context_path, local_type)
        if not os.path.isdir(dir_path):
            continue

        for file_name in os.listdir(dir_path):
            device_name = os.path.splitext(file_name)[0]
            msg = f"Loading local config context for `{device_name}` from `{local_type}/{file_name}`"
            logger.info(msg)
            job_result.log(msg, grouping="local config contexts")
            try:
                with open(os.path.join(dir_path, file_name), "r") as fd:
                    context_data = yaml.safe_load(fd)

                import_local_config_context(
                    local_type,
                    device_name,
                    context_data,
                    repository_record,
                )
                managed_local_config_contexts[local_type].add(device_name)
            except Exception as exc:
                msg = f"Error in loading local config context from `{local_type}/{file_name}`: {exc}"
                logger.error(msg)
                job_result.log(msg, level_choice=LogLevelChoices.LOG_ERROR, grouping="local config contexts")

    # Delete any prior contexts that are owned by this repository but were not created/updated above
    delete_git_config_contexts(
        repository_record,
        job_result,
        preserve=managed_config_contexts,
        preserve_local=managed_local_config_contexts,
    )


def import_config_context(context_data, repository_record, job_result):
    """
    Parse a given dictionary of data to create/update a ConfigContext record.

    The dictionary is expected to have a key "_metadata" which defines properties on the ConfigContext record itself
    (name, weight, description, etc.), while all other keys in the dictionary will go into the record's "data" field.

    Note that we don't use extras.api.serializers.ConfigContextSerializer, despite superficial similarities;
    the reason is that the serializer only allows us to identify related objects (Locations, Role, etc.)
    by their database primary keys, whereas here we need to be able to look them up by other values such as name.
    """
    git_repository_content_type = ContentType.objects.get_for_model(GitRepository)

    context_record = None
    # TODO: check context_data against a schema of some sort?

    if "_metadata" not in context_data:
        raise RuntimeError("data is missing the required `_metadata` key.")
    if "name" not in context_data["_metadata"]:
        raise RuntimeError("data `_metadata` is missing the required `name` key.")

    # Set defaults for optional fields
    context_metadata = context_data["_metadata"]
    context_metadata.setdefault("weight", 1000)
    context_metadata.setdefault("description", "")
    context_metadata.setdefault("is_active", True)

    # Context Metadata `schema` has been updated to `config_context_schema`,
    # but for backwards compatibility `schema` is still supported.
    if "schema" in context_metadata and "config_context_schema" not in context_metadata:
        msg = "`schema` is deprecated in `_metadata`, please use `config_context_schema` instead."
        logger.warning(msg)
        job_result.log(msg, level_choice=LogLevelChoices.LOG_WARNING, grouping="config context")
        context_metadata["config_context_schema"] = context_metadata.pop("schema")

    # Translate relationship queries/filters to lists of related objects
    relations = {}
    for key, model_class in [
        ("locations", Location),
        ("device_types", DeviceType),
        ("roles", Role),
        ("platforms", Platform),
        ("cluster_groups", ClusterGroup),
        ("clusters", Cluster),
        ("tenant_groups", TenantGroup),
        ("tenants", Tenant),
        ("tags", Tag),
        ("dynamic_groups", DynamicGroup),
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

        if context_metadata.get("config_context_schema"):
            if getattr(context_record.config_context_schema, "name", None) != context_metadata["config_context_schema"]:
                try:
                    schema = ConfigContextSchema.objects.get(name=context_metadata["config_context_schema"])
                    context_record.config_context_schema = schema
                    modified = True
                except ConfigContextSchema.DoesNotExist:
                    msg = f"ConfigContextSchema {context_metadata['config_context_schema']} does not exist."
                    logger.error(msg)
                    job_result.log(
                        msg, obj=context_record, level_choice=LogLevelChoices.LOG_ERROR, grouping="config contexts"
                    )
        else:
            if context_record.config_context_schema is not None:
                context_record.config_context_schema = None
                modified = True

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
        msg = "Successfully created config context"
        logger.info(msg)
        job_result.log(msg, obj=context_record, level_choice=LogLevelChoices.LOG_INFO, grouping="config contexts")
    elif modified:
        msg = "Successfully refreshed config context"
        logger.info(msg)
        job_result.log(msg, obj=context_record, level_choice=LogLevelChoices.LOG_INFO, grouping="config contexts")
    else:
        msg = "No change to config context"
        logger.info(msg)
        job_result.log(msg, obj=context_record, level_choice=LogLevelChoices.LOG_INFO, grouping="config contexts")

    return context_record.name if context_record else None


def import_local_config_context(local_type, device_name, context_data, repository_record):
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
        raise RuntimeError("multiple records with the same name found; unable to determine which one to apply to!")
    except ObjectDoesNotExist:
        raise RuntimeError("record not found!")

    if (
        record.local_config_context_data_owner is not None
        and record.local_config_context_data_owner != repository_record
    ):
        logger.error(
            "DATA CONFLICT: Local context data is owned by another owner, %s",
            record.local_config_context_data_owner,
            extra={"object": record, "grouping": "local config contexts"},
        )
        return

    if record.local_config_context_data == context_data and record.local_config_context_data_owner == repository_record:
        logger.info("No change to local config context", extra={"object": record, "grouping": "local config contexts"})
        return

    record.local_config_context_data = context_data
    record.local_config_context_data_owner = repository_record
    record.clean()
    record.save()
    logger.info(
        "Successfully updated local config context", extra={"object": record, "grouping": "local config contexts"}
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
            msg = f"Deleted config context {context_record}"
            logger.warning(msg)
            job_result.log(msg, level_choice=LogLevelChoices.LOG_WARNING, grouping="config contexts")

    for grouping, model in (
        ("devices", Device),
        ("virtual_machines", VirtualMachine),
    ):
        for record in model.objects.filter(
            local_config_context_data_owner_content_type=git_repository_content_type,
            local_config_context_data_owner_object_id=repository_record.pk,
        ):
            if record.name not in preserve_local[grouping]:
                record.local_config_context_data = None
                record.local_config_context_data_owner = None
                record.clean()
                record.save()
                msg = "Deleted local config context"
                logger.warning(msg)
                job_result.log(
                    msg, obj=record, level_choice=LogLevelChoices.LOG_WARNING, grouping="local config contexts"
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
    config_context_schema_path = os.path.join(repository_record.filesystem_path, "config_context_schemas")
    if not os.path.isdir(config_context_schema_path):
        return

    managed_config_context_schemas = set()

    for file_name in os.listdir(config_context_schema_path):
        if not os.path.isfile(os.path.join(config_context_schema_path, file_name)):
            continue
        msg = (f"Loading config context schema from `{file_name}`",)
        logger.info(msg)
        job_result.log(msg, grouping="config context schemas")
        try:
            with open(os.path.join(config_context_schema_path, file_name), "r") as fd:
                # The data file can be either JSON or YAML; since YAML is a superset of JSON, we can load it regardless
                context_schema_data = yaml.safe_load(fd)

            # A file can contain one config context dict or a list thereof
            if isinstance(context_schema_data, dict):
                context_name = import_config_context_schema(context_schema_data, repository_record, job_result)
                managed_config_context_schemas.add(context_name)
            elif isinstance(context_schema_data, list):
                for context_schema in context_schema_data:
                    if isinstance(context_schema, dict):
                        context_name = import_config_context_schema(context_schema, repository_record, job_result)
                        managed_config_context_schemas.add(context_name)
                    else:
                        raise RuntimeError("each item in list data must be a dict")
            else:
                raise RuntimeError("data must be a dict or a list of dicts")
        except Exception as exc:
            msg = f"Error in loading config context schema data from `{file_name}`: {exc}"
            logger.error(msg)
            job_result.log(msg, level_choice=LogLevelChoices.LOG_ERROR, grouping="config context schemas")

    # Delete any prior contexts that are owned by this repository but were not created/updated above
    delete_git_config_context_schemas(
        repository_record,
        job_result,
        preserve=managed_config_context_schemas,
    )


def import_config_context_schema(context_schema_data, repository_record, job_result):
    """Using data from schema file, create schema record in Nautobot."""
    git_repository_content_type = ContentType.objects.get_for_model(GitRepository)

    created = False
    modified = False

    if "_metadata" not in context_schema_data:
        raise RuntimeError("data is missing the required `_metadata` key.")
    if "name" not in context_schema_data["_metadata"]:
        raise RuntimeError("data `_metadata` is missing the required `name` key.")

    schema_metadata = context_schema_data["_metadata"]

    try:
        schema_record = ConfigContextSchema.objects.get(
            name=schema_metadata["name"],
            owner_content_type=git_repository_content_type,
            owner_object_id=repository_record.pk,
        )
    except ConfigContextSchema.DoesNotExist:
        schema_record = ConfigContextSchema(
            name=schema_metadata["name"],
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
        msg = "Successfully created config context schema"
        logger.info(msg)
        job_result.log(msg, obj=schema_record, level_choice=LogLevelChoices.LOG_INFO, grouping="config context schemas")
    elif modified:
        schema_record.validated_save()
        msg = "Successfully refreshed config context schema"
        logger.info(msg)
        job_result.log(msg, obj=schema_record, level_choice=LogLevelChoices.LOG_INFO, grouping="config context schemas")
    else:
        msg = "No change to config context schema"
        logger.info(msg)
        job_result.log(msg, obj=schema_record, level_choice=LogLevelChoices.LOG_INFO, grouping="config context schemas")

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
            msg = f"Deleted config context schema {schema_record}"
            logger.warning(msg)
            job_result.log(msg, level_choice=LogLevelChoices.LOG_WARNING, grouping="config context schemas")


#
# Job handling
#


def refresh_code_from_repository(repository_slug, consumer=None, skip_reimport=False):
    """
    After cloning/updating a GitRepository on disk, call this function to reload and reregister the repo's Python code.

    Args:
        repository_slug (str): Repository directory in GIT_ROOT that was refreshed.
        consumer (celery.worker.Consumer): Celery Consumer to update as well
        skip_reimport (bool): If True, unload existing code from this repository but do not re-import it.
    """
    if settings.GIT_ROOT not in sys.path:
        sys.path.append(settings.GIT_ROOT)

    app = consumer.app if consumer is not None else celery_app
    # TODO: This is ugly, but when app.use_fast_trace_task is set (true by default), Celery calls
    # celery.app.trace.fast_trace_task(...) which assumes that all tasks are cached and have a valid `__trace__()`
    # function defined. In theory consumer.update_strategies() (below) should ensure this, but it doesn't
    # go far enough (possibly a discrepancy between the main worker process and the prefork executors?)
    # as we can and do still encounter errors where `task.__trace__` is unexpectedly None.
    # For now, simply disabling use_fast_trace_task forces the task trace function to be rebuilt each time,
    # which avoids the issue at the cost of very slight overhead.
    app.use_fast_trace_task = False

    # Unload any previous version of this module and its submodules if present
    for module_name in list(sys.modules):
        if module_name == repository_slug or module_name.startswith(f"{repository_slug}."):
            logger.debug("Unloading module %s", module_name)
            if module_name in app.loader.task_modules:
                app.loader.task_modules.remove(module_name)
            del sys.modules[module_name]

    # Unregister any previous Celery tasks from this module
    for task_name in list(app.tasks):
        if task_name.startswith(f"{repository_slug}."):
            logger.debug("Unregistering Celery task %s", task_name)
            app.tasks.unregister(task_name)
            if consumer is not None:
                del consumer.strategies[task_name]

    if not skip_reimport:
        try:
            repository = GitRepository.objects.get(slug=repository_slug)
            if "extras.job" in repository.provided_contents:
                # Re-import Celery tasks from this module
                logger.debug("Importing Jobs from %s.jobs in GIT_ROOT", repository_slug)
                app.loader.import_task_module(f"{repository_slug}.jobs")
                if consumer is not None:
                    consumer.update_strategies()
        except GitRepository.DoesNotExist as exc:
            logger.error("Unable to reload Jobs from %s.jobs: %s", repository_slug, exc)
            raise


def refresh_git_jobs(repository_record, job_result, delete=False):
    """Callback function for GitRepository updates - refresh all Job records managed by this repository."""
    installed_jobs = []
    if "extras.job" in repository_record.provided_contents and not delete:
        found_jobs = False
        try:
            refresh_code_from_repository(repository_record.slug)

            for task_name, task in celery_app.tasks.items():
                if not task_name.startswith(f"{repository_record.slug}."):
                    continue
                found_jobs = True
                job_model, created = refresh_job_model_from_job_class(Job, task.__class__)

                if job_model is None:
                    msg = "Failed to create Job record; check Nautobot logs for details"
                    logger.error(msg)
                    job_result.log(msg, grouping="jobs", level_choice=LogLevelChoices.LOG_ERROR)
                    continue

                if created:
                    message = "Created Job record"
                else:
                    message = "Refreshed Job record"
                logger.info(message)
                job_result.log(message=message, obj=job_model, grouping="jobs", level_choice=LogLevelChoices.LOG_INFO)
                installed_jobs.append(job_model)

            if not found_jobs:
                msg = "No jobs were registered on loading the `jobs` submodule. Did you miss a `register_jobs()` call?"
                logger.warning(msg)
                job_result.log(msg, grouping="jobs", level_choice=LogLevelChoices.LOG_WARNING)
        except Exception as exc:
            msg = f"Error in loading Jobs from Git repository: {exc}"
            logger.error(msg)
            job_result.log(msg, grouping="jobs", level_choice=LogLevelChoices.LOG_ERROR)
    else:
        # Unload code from this repository, do not reimport it
        refresh_code_from_repository(repository_record.slug, skip_reimport=True)

    for job_model in Job.objects.filter(module_name__startswith=f"{repository_record.slug}."):
        if job_model.installed and job_model not in installed_jobs:
            msg = "Marking Job record as no longer installed"
            logger.warning(msg)
            job_result.log(msg, obj=job_model, grouping="jobs", level_choice=LogLevelChoices.LOG_WARNING)
            job_model.installed = False
            job_model.save()


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
    # Error checking - did the user put directories in the repository root instead of under /export_templates/?
    for app_label in ["circuits", "dcim", "extras", "ipam", "tenancy", "users", "virtualization"]:
        unexpected_path = os.path.join(repository_record.filesystem_path, app_label)
        if os.path.isdir(unexpected_path):
            msg = (
                f'Found "{app_label}" directory in the repository root. If this is meant to contain export templates, '
                "it should be moved into an `export_templates/` subdirectory."
            )
            logger.warning(msg)
            job_result.log(msg, level_choice=LogLevelChoices.LOG_WARNING, grouping="export templates")

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
        msg = f"Loading `{app_label}.{modelname}` export template from `{file_name}`"
        logger.info(msg)
        job_result.log(msg, grouping="export templates")
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

            # mimetypes.guess_type returns a tuple (type, encoding)
            mime_type = mimetypes.guess_type(file_path)[0]
            if mime_type is None:
                mime_type = "text/plain"
            if template_record.mime_type != mime_type:
                template_record.mime_type = mime_type
                modified = True

            if template_record.file_extension != file_name.rsplit(os.extsep, 1)[-1]:
                template_record.file_extension = file_name.rsplit(os.extsep, 1)[-1]
                modified = True

            if modified:
                template_record.save()

            if created:
                msg = "Successfully created export template"
                logger.info(msg)
                job_result.log(
                    msg, obj=template_record, level_choice=LogLevelChoices.LOG_INFO, grouping="export templates"
                )
            elif modified:
                msg = "Successfully refreshed export template"
                logger.info(msg)
                job_result.log(
                    msg, obj=template_record, level_choice=LogLevelChoices.LOG_INFO, grouping="export templates"
                )
            else:
                msg = "No change to export template"
                logger.info(msg)
                job_result.log(
                    msg, obj=template_record, level_choice=LogLevelChoices.LOG_INFO, grouping="export templates"
                )

        except Exception as exc:
            logger.error(str(exc))
            job_result.log(
                str(exc), obj=template_record, level_choice=LogLevelChoices.LOG_ERROR, grouping="export templates"
            )

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
        key = f"{template_record.content_type.app_label}.{template_record.content_type.model}"
        if template_record.name not in preserve.get(key, ()):
            template_record.delete()
            msg = f"Deleted export template {template_record}"
            logger.warning(msg)
            job_result.log(msg, level_choice=LogLevelChoices.LOG_WARNING, grouping="export templates")


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
