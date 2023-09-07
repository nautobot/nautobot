import contextvars
import os
import random
import shutil
import logging
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.signals import m2m_changed, pre_delete, post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django_prometheus.models import model_deletes, model_inserts, model_updates

from nautobot.core.celery import app, import_jobs_as_celery_tasks
from nautobot.core.utils.config import get_settings_or_config
from nautobot.extras.tasks import delete_custom_field_data, provision_field
from nautobot.extras.utils import refresh_job_model_from_job_class
from nautobot.extras.constants import CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL
from .choices import JobResultStatusChoices, ObjectChangeActionChoices
from .models import CustomField, DynamicGroup, DynamicGroupMembership, GitRepository, JobResult, ObjectChange
from .webhooks import enqueue_webhooks


# thread safe change context state variable
change_context_state = contextvars.ContextVar("change_context_state", default=None)
logger = logging.getLogger(__name__)


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


@receiver(post_save)
@receiver(m2m_changed)
def _handle_changed_object(sender, instance, raw=False, **kwargs):
    """
    Fires when an object is created or updated.
    """
    from .jobs import enqueue_job_hooks  # avoid circular import

    if raw:
        return

    if change_context_state.get() is None:
        return

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
        # save a copy of this instance's field cache so it can be restored after serialization
        # to prevent unexpected behavior when chaining multiple signal handlers
        original_cache = instance._state.fields_cache.copy()
        if object_m2m_changed:
            related_changes = ObjectChange.objects.filter(
                changed_object_type=ContentType.objects.get_for_model(instance),
                changed_object_id=instance.pk,
                request_id=change_context_state.get().change_id,
            )
            m2m_changes = instance.to_objectchange(action)
            related_changes.update(object_data=m2m_changes.object_data, object_data_v2=m2m_changes.object_data_v2)
            objectchange = related_changes.first() if related_changes.exists() else None
        else:
            objectchange = instance.to_objectchange(action)
            objectchange.user = _get_user_if_authenticated(change_context_state.get().get_user(), objectchange)
            objectchange.request_id = change_context_state.get().change_id
            objectchange.change_context = change_context_state.get().context
            objectchange.change_context_detail = change_context_state.get().context_detail[
                :CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL
            ]
            objectchange.save()

        # restore field cache
        instance._state.fields_cache = original_cache

        # Enqueue job hooks
        if objectchange is not None:
            enqueue_job_hooks(objectchange)

    # Enqueue webhooks
    enqueue_webhooks(instance, change_context_state.get().get_user(), change_context_state.get().change_id, action)

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


@receiver(pre_delete)
def _handle_deleted_object(sender, instance, **kwargs):
    """
    Fires when an object is deleted.
    """
    from .jobs import enqueue_job_hooks  # avoid circular import

    if change_context_state.get() is None:
        return

    # Record an ObjectChange if applicable
    if hasattr(instance, "to_objectchange"):
        # save a copy of this instance's field cache so it can be restored after serialization
        # to prevent unexpected behavior when chaining multiple signal handlers
        original_cache = instance._state.fields_cache.copy()
        objectchange = instance.to_objectchange(ObjectChangeActionChoices.ACTION_DELETE)
        objectchange.user = _get_user_if_authenticated(change_context_state.get().get_user(), objectchange)
        objectchange.request_id = change_context_state.get().change_id
        objectchange.change_context = change_context_state.get().context
        objectchange.change_context_detail = change_context_state.get().context_detail[
            :CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL
        ]
        objectchange.save()

        # restore field cache
        instance._state.fields_cache = original_cache

        # Enqueue job hooks
        enqueue_job_hooks(objectchange)

    # Enqueue webhooks
    enqueue_webhooks(
        instance,
        change_context_state.get().get_user(),
        change_context_state.get().change_id,
        ObjectChangeActionChoices.ACTION_DELETE,
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
        transaction.on_commit(lambda: delete_custom_field_data.delay(instance.key, pk_set))

    elif action == "post_add":
        # New content types have been added to the custom field, provision them
        transaction.on_commit(lambda: provision_field.delay(instance.pk, pk_set))


m2m_changed.connect(handle_cf_removed_obj_types, sender=CustomField.content_types.through)


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

    # FIXME(jathan): In light of jobs overhaul and Git syncs as jobs, we need to rethink this. We
    # might instead make "delete" another Job class and call it here, but also think about how
    # worker events will be such as firing the worker event here.
    job_result = JobResult.objects.create(
        name=instance.name,
        user=None,
        status=JobResultStatusChoices.STATUS_STARTED,
    )

    # This isn't running in the context of a Job execution transaction,
    # so there's no need to use the "job_logs" proxy DB.
    # In fact, attempting to do so would cause database IntegrityErrors!
    job_result.use_job_logs_db = False

    refresh_datasource_content("extras.gitrepository", instance, None, job_result, delete=True)

    # In a distributed Nautobot deployment, each Django instance and/or worker instance may have its own clone
    # of this repository; we need some way to ensure that all such clones are deleted.
    # In the Celery worker case, we can broadcast a control message to all workers to do so:
    app.control.broadcast("discard_git_repository", repository_slug=instance.slug)
    # But we don't have an equivalent way to broadcast to any other Django instances.
    # For now we just delete the one that we have locally and rely on other methods,
    # such as the import_jobs_as_celery_tasks() signal that runs on server startup,
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


def dynamic_group_membership_created(sender, instance, raw=False, **kwargs):
    """
    Forcibly call `full_clean()` when a new `DynamicGroupMembership` object
    is manually created to prevent inadvertantly creating invalid memberships.
    """
    if raw:
        return
    instance.full_clean()


m2m_changed.connect(dynamic_group_children_changed, sender=DynamicGroup.children.through)
pre_save.connect(dynamic_group_membership_created, sender=DynamicGroupMembership)


def dynamic_group_eligible_groups_changed(sender, instance, **kwargs):
    """
    When a DynamicGroup is created or deleted, refresh the cache of eligible groups for the associated ContentType.

    Can't change content_type_id on an existing instance, so no need to check for that.
    """

    if get_settings_or_config("DYNAMIC_GROUPS_MEMBER_CACHE_TIMEOUT") == 0:
        # Caching is disabled, so there's nothing to do
        return

    if kwargs.get("created", None) is False:
        # We do not care about updates
        # "created" is not a kwarg for post_delete signals, so is unset or None
        # "created" is a kwarg for post_save signals, but you cannot change content types of existing groups
        #   therefor we can ignore cache updates on DynamicGroups updates
        return

    content_type = instance.content_type
    cache_key = f"{content_type.app_label}.{content_type.model}._get_eligible_dynamic_groups"
    cache.set(
        cache_key,
        DynamicGroup.objects.filter(content_type_id=instance.content_type_id),
        get_settings_or_config("DYNAMIC_GROUPS_MEMBER_CACHE_TIMEOUT"),
    )


post_save.connect(dynamic_group_eligible_groups_changed, sender=DynamicGroup)
post_delete.connect(dynamic_group_eligible_groups_changed, sender=DynamicGroup)


def dynamic_group_update_cached_members(sender, instance, **kwargs):
    """
    When a DynamicGroup or DynamicGroupMembership is updated, update the cache of members.
    """

    if get_settings_or_config("DYNAMIC_GROUPS_MEMBER_CACHE_TIMEOUT") == 0:
        # Caching is disabled, so there's nothing to do
        return

    if isinstance(instance, DynamicGroupMembership):
        group = instance.group
    else:
        group = instance

    def _update_cache_and_parents(this_instance):
        this_instance.update_cached_members()

        # Since a change a group or group of groups does not affect it's children, we only need to go up the tree
        # A group of groups does not use the cache of it's children due to the complexity of the set operations
        for ancestor in list(this_instance.parents.all()):
            _update_cache_and_parents(ancestor)

    _update_cache_and_parents(group)


post_save.connect(dynamic_group_update_cached_members, sender=DynamicGroup)
post_save.connect(dynamic_group_update_cached_members, sender=DynamicGroupMembership)


#
# Jobs
#


def refresh_job_models(sender, *, apps, **kwargs):
    """
    Callback for the nautobot_database_ready signal; updates Jobs in the database based on Job source file availability.
    """
    from nautobot.extras.jobs import Job as JobClass  # avoid circular import

    Job = apps.get_model("extras", "Job")

    # To make reverse migrations safe
    if not hasattr(Job, "job_class_name"):
        logger.info("Skipping refresh_job_models() as it appears Job model has not yet been migrated to latest.")
        return

    import_jobs_as_celery_tasks(app)

    job_models = []
    for task in app.tasks.values():
        # Skip Celery tasks that aren't Jobs
        if not isinstance(task, JobClass):
            continue

        job_model, _ = refresh_job_model_from_job_class(Job, task.__class__)
        if job_model is not None:
            job_models.append(job_model)

    for job_model in Job.objects.filter(installed=True):
        if job_model not in job_models:
            logger.info(
                "Job %s/%s is no longer installed",
                job_model.module_name,
                job_model.job_class_name,
            )
            job_model.installed = False
            job_model.save()
