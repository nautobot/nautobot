import os
import random
import shutil
import uuid
import logging
from datetime import timedelta

from cacheops.signals import cache_invalidated, cache_read
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.signals import m2m_changed, pre_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django_prometheus.models import model_deletes, model_inserts, model_updates
from prometheus_client import Counter

from nautobot.extras.tasks import delete_custom_field_data, provision_field
from nautobot.extras.utils import refresh_job_model_from_job_class
from nautobot.utilities.config import get_settings_or_config
from nautobot.extras.constants import CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL
from .choices import JobResultStatusChoices, ObjectChangeActionChoices
from .models import CustomField, DynamicGroup, DynamicGroupMembership, GitRepository, JobResult, ObjectChange
from .webhooks import enqueue_webhooks

logger = logging.getLogger("nautobot.extras.signals")


#
# Change logging/webhooks
#


def _get_user_if_authenticated(user, objectchange):
    """Return the user object associated with the request if the user is defined.

    If the user is not defined, log a warning to indicate that the user couldn't be retrived from the request
    This is a workaround to fix a recurring issue where the user shouldn't be present in the request object randomly.
    A similar issue was reported in NetBox https://github.com/netbox-community/netbox/issues/5142
    """
    if user.is_authenticated:
        return user
    else:
        logger.warning(f"Unable to retrieve the user while creating the changelog for {objectchange.changed_object}")
        return None


def _handle_changed_object(change_context, sender, instance, **kwargs):
    """
    Fires when an object is created or updated.
    """
    from .jobs import enqueue_job_hooks  # avoid circular import

    object_m2m_changed = False

    # Determine the type of change being made
    if kwargs.get("created"):
        action = ObjectChangeActionChoices.ACTION_CREATE
    elif "created" in kwargs:
        action = ObjectChangeActionChoices.ACTION_UPDATE
    elif kwargs.get("action") in ["post_add", "post_remove"] and kwargs["pk_set"]:
        # m2m_changed with objects added or removed
        object_m2m_changed = True
        action = ObjectChangeActionChoices.ACTION_UPDATE
    else:
        return

    # Record an ObjectChange if applicable
    if hasattr(instance, "to_objectchange"):
        if object_m2m_changed:
            related_changes = ObjectChange.objects.filter(
                changed_object_type=ContentType.objects.get_for_model(instance),
                changed_object_id=instance.pk,
                request_id=change_context.change_id,
            )
            m2m_changes = instance.to_objectchange(action)
            related_changes.update(object_data=m2m_changes.object_data, object_data_v2=m2m_changes.object_data_v2)
            objectchange = related_changes.first() if related_changes.exists() else None
        else:
            objectchange = instance.to_objectchange(action)
            objectchange.user = _get_user_if_authenticated(change_context.get_user(), objectchange)
            objectchange.request_id = change_context.change_id
            objectchange.change_context = change_context.context
            objectchange.change_context_detail = change_context.context_detail[:CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL]
            objectchange.save()

        # Enqueue job hooks
        if objectchange is not None:
            enqueue_job_hooks(objectchange)

    # Enqueue webhooks
    enqueue_webhooks(instance, change_context.get_user(), change_context.change_id, action)

    # Increment metric counters
    if action == ObjectChangeActionChoices.ACTION_CREATE:
        model_inserts.labels(instance._meta.model_name).inc()
    elif action == ObjectChangeActionChoices.ACTION_UPDATE:
        model_updates.labels(instance._meta.model_name).inc()

    # Housekeeping: 0.1% chance of clearing out expired ObjectChanges
    changelog_retention = get_settings_or_config("CHANGELOG_RETENTION")
    if changelog_retention and random.randint(1, 1000) == 1:
        cutoff = timezone.now() - timedelta(days=changelog_retention)
        ObjectChange.objects.filter(time__lt=cutoff).delete()


def _handle_deleted_object(change_context, sender, instance, **kwargs):
    """
    Fires when an object is deleted.
    """
    from .jobs import enqueue_job_hooks  # avoid circular import

    # Record an ObjectChange if applicable
    if hasattr(instance, "to_objectchange"):
        objectchange = instance.to_objectchange(ObjectChangeActionChoices.ACTION_DELETE)
        objectchange.user = _get_user_if_authenticated(change_context.get_user(), objectchange)
        objectchange.request_id = change_context.change_id
        objectchange.change_context = change_context.context
        objectchange.change_context_detail = change_context.context_detail[:CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL]
        objectchange.save()

        # Enqueue job hooks
        enqueue_job_hooks(objectchange)

    # Enqueue webhooks
    enqueue_webhooks(
        instance, change_context.get_user(), change_context.change_id, ObjectChangeActionChoices.ACTION_DELETE
    )

    # Increment metric counters
    model_deletes.labels(instance._meta.model_name).inc()


#
# Custom fields
#


def handle_cf_removed_obj_types(instance, action, pk_set, **kwargs):
    """
    Handle the cleanup of old custom field data when a CustomField is removed from one or more ContentTypes.
    """
    if action == "post_remove":
        # Existing content types have been removed from the custom field, delete their data
        # 2.0 TODO: #824 instance.slug rather than instance.name
        transaction.on_commit(lambda: delete_custom_field_data.delay(instance.name, pk_set))

    elif action == "post_add":
        # New content types have been added to the custom field, provision them
        transaction.on_commit(lambda: provision_field.delay(instance.pk, pk_set))


m2m_changed.connect(handle_cf_removed_obj_types, sender=CustomField.content_types.through)


#
# Caching
#

cacheops_cache_hit = Counter("cacheops_cache_hit", "Number of cache hits")
cacheops_cache_miss = Counter("cacheops_cache_miss", "Number of cache misses")
cacheops_cache_invalidated = Counter("cacheops_cache_invalidated", "Number of cache invalidations")


def cache_read_collector(sender, func, hit, **kwargs):
    if hit:
        cacheops_cache_hit.inc()
    else:
        cacheops_cache_miss.inc()


def cache_invalidated_collector(sender, obj_dict, **kwargs):
    cacheops_cache_invalidated.inc()


cache_read.connect(cache_read_collector)
cache_invalidated.connect(cache_invalidated_collector)


#
# Datasources
#


@receiver(pre_delete, sender=GitRepository)
def git_repository_pre_delete(instance, **kwargs):
    """
    When a GitRepository is deleted, invoke all registered callbacks, then remove it from the local filesystem.

    Note that GitRepository create/update operations enqueue a background job to handle the sync/resync;
    this operation, by contrast, happens in the foreground as it needs to complete before we allow the
    GitRepository itself to be deleted.
    """
    from nautobot.extras.datasources import refresh_datasource_content

    job_result = JobResult.objects.create(
        name=instance.name,
        obj_type=ContentType.objects.get_for_model(instance),
        user=None,
        job_id=uuid.uuid4(),
        status=JobResultStatusChoices.STATUS_RUNNING,
    )

    # This isn't running in the context of a Job execution transaction,
    # so there's no need to use the "job_logs" proxy DB.
    # In fact, attempting to do so would cause database IntegrityErrors!
    job_result.use_job_logs_db = False

    refresh_datasource_content("extras.gitrepository", instance, None, job_result, delete=True)

    if job_result.status not in JobResultStatusChoices.TERMINAL_STATE_CHOICES:
        job_result.set_status(JobResultStatusChoices.STATUS_COMPLETED)
    job_result.save()

    # TODO: In a distributed Nautobot deployment, each Django instance and/or worker instance may have its own clone
    # of this repository; we need some way to ensure that all such clones are deleted.
    # For now we just delete the one that we have locally and rely on other methods (notably get_jobs())
    # to clean up other clones as they're encountered.
    if os.path.isdir(instance.filesystem_path):
        shutil.rmtree(instance.filesystem_path)


#
# Dynamic Groups
#


def dynamic_group_children_changed(sender, instance, action, reverse, model, pk_set, **kwargs):
    """
    Disallow adding DynamicGroup children if the parent has a filter.
    """
    if action == "pre_add" and instance.filter:
        raise ValidationError(
            {
                "children": "A parent group may have either a filter or child groups, but not both. Clear the parent filter and try again."
            }
        )


def dynamic_group_membership_created(sender, instance, **kwargs):
    """
    Forcibly call `full_clean()` when a new `DynamicGroupMembership` object
    is manually created to prevent inadvertantly creating invalid memberships.
    """
    instance.full_clean()


m2m_changed.connect(dynamic_group_children_changed, sender=DynamicGroup.children.through)
pre_save.connect(dynamic_group_membership_created, sender=DynamicGroupMembership)


#
# Jobs
#


def refresh_job_models(sender, *, apps, **kwargs):
    """
    Callback for the nautobot_database_ready signal; updates Jobs in the database based on Job source file availability.
    """
    Job = apps.get_model("extras", "Job")
    GitRepository = apps.get_model("extras", "GitRepository")  # pylint: disable=redefined-outer-name

    # To make reverse migrations safe
    if not hasattr(Job, "job_class_name") or not hasattr(Job, "git_repository"):
        logger.info("Skipping refresh_job_models() as it appears Job model has not yet been migrated to latest.")
        return

    from nautobot.extras.jobs import get_jobs

    # TODO: eventually this should be inverted so that get_jobs() relies on the database models...
    job_classes = get_jobs()
    job_models = []
    for source, modules in job_classes.items():
        git_repository = None
        if source.startswith("git."):
            try:
                git_repository = GitRepository.objects.get(slug=source[4:])
            except GitRepository.DoesNotExist:
                logger.warning('GitRepository "%s" not found?', source[4:])
            source = "git"

        for module_details in modules.values():
            for job_class in module_details["jobs"].values():
                # TODO: catch DB error in case where multiple Jobs have the same grouping + name
                job_model, _ = refresh_job_model_from_job_class(Job, source, job_class, git_repository=git_repository)
                if job_model is not None:
                    job_models.append(job_model)

    for job_model in Job.objects.all():
        if job_model.installed and job_model not in job_models:
            logger.info(
                "Job %s%s/%s/%s is no longer installed",
                job_model.source,
                f"/{job_model.git_repository.slug}" if job_model.git_repository is not None else "",
                job_model.module_name,
                job_model.job_class_name,
            )
            job_model.installed = False
            job_model.save()
