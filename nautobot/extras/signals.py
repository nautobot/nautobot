import contextlib
import contextvars
import logging
import os
import shutil
import traceback

from db_file_storage.model_utils import delete_file
from db_file_storage.storage import DatabaseFileStorage
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.storage import get_storage_class
from django.db import transaction
from django.db.models.signals import m2m_changed, post_delete, post_migrate, post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django_prometheus.models import model_deletes, model_inserts, model_updates
import redis.exceptions

from nautobot.core.celery import app, import_jobs
from nautobot.core.models import BaseModel
from nautobot.core.utils.logging import sanitize
from nautobot.extras.choices import JobResultStatusChoices, ObjectChangeActionChoices
from nautobot.extras.constants import CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL
from nautobot.extras.models import (
    ComputedField,
    ContactAssociation,
    CustomField,
    DynamicGroup,
    DynamicGroupMembership,
    GitRepository,
    JobResult,
    MetadataType,
    ObjectChange,
    Relationship,
)
from nautobot.extras.querysets import NotesQuerySet
from nautobot.extras.tasks import delete_custom_field_data, provision_field
from nautobot.extras.utils import refresh_job_model_from_job_class

# thread safe change context state variable
change_context_state = contextvars.ContextVar("change_context_state", default=None)
logger = logging.getLogger(__name__)


#
# Change logging
#


def get_user_if_authenticated(user, instance):
    """Return the user object associated with the request if the user is defined.

    If the user is not defined, log a warning to indicate that the user couldn't be retrived from the request
    This is a workaround to fix a recurring issue where the user shouldn't be present in the request object randomly.
    A similar issue was reported in NetBox https://github.com/netbox-community/netbox/issues/5142
    """
    if user.is_authenticated:
        return user
    else:
        logger.warning(f"Unable to retrieve the user while creating the changelog for {instance}")
        return None


@receiver(post_save, sender=ComputedField)
@receiver(post_save, sender=CustomField)
@receiver(post_save, sender=CustomField.content_types.through)
@receiver(post_save, sender=MetadataType)
@receiver(post_save, sender=MetadataType.content_types.through)
@receiver(m2m_changed, sender=ComputedField)
@receiver(m2m_changed, sender=CustomField)
@receiver(m2m_changed, sender=CustomField.content_types.through)
@receiver(m2m_changed, sender=MetadataType)
@receiver(m2m_changed, sender=MetadataType.content_types.through)
@receiver(post_delete, sender=ComputedField)
@receiver(post_delete, sender=CustomField)
@receiver(post_delete, sender=CustomField.content_types.through)
@receiver(post_delete, sender=MetadataType)
@receiver(post_delete, sender=MetadataType.content_types.through)
def invalidate_models_cache(sender, **kwargs):
    """Invalidate the related-models cache for ComputedFields and CustomFields."""
    if sender is CustomField.content_types.through:
        manager = CustomField.objects
    elif sender is MetadataType.content_types.through:
        manager = MetadataType.objects
    else:
        manager = sender.objects

    with contextlib.suppress(redis.exceptions.ConnectionError):
        # TODO: *maybe* target more narrowly, e.g. only clear the cache for specific related content-types?
        cache.delete_pattern(f"{manager.get_for_model.cache_key_prefix}.*")


@receiver(post_save, sender=Relationship)
@receiver(m2m_changed, sender=Relationship)
@receiver(post_delete, sender=Relationship)
def invalidate_relationship_models_cache(sender, **kwargs):
    """Invalidate the related-models caches for Relationships."""
    for method in (
        Relationship.objects.get_for_model_source,
        Relationship.objects.get_for_model_destination,
    ):
        with contextlib.suppress(redis.exceptions.ConnectionError):
            # TODO: *maybe* target more narrowly, e.g. only clear the cache for specific related content-types?
            cache.delete_pattern(f"{method.cache_key_prefix}.*")


@receiver(post_save)
@receiver(m2m_changed)
def _handle_changed_object(sender, instance, raw=False, **kwargs):
    """
    Fires when an object is created or updated.
    """

    if raw:
        return

    change_context = change_context_state.get()

    if change_context is None:
        return

    # Determine the type of change being made
    if kwargs.get("created"):
        action = ObjectChangeActionChoices.ACTION_CREATE
    elif "created" in kwargs:
        action = ObjectChangeActionChoices.ACTION_UPDATE
    elif kwargs.get("action") in ["post_add", "post_remove"] and kwargs["pk_set"]:
        # m2m_changed with objects added or removed
        action = ObjectChangeActionChoices.ACTION_UPDATE
    else:
        return

    # Record an ObjectChange if applicable
    if hasattr(instance, "to_objectchange"):
        user = change_context.get_user(instance)
        # save a copy of this instance's field cache so it can be restored after serialization
        # to prevent unexpected behavior when chaining multiple signal handlers
        original_cache = instance._state.fields_cache.copy()

        changed_object_type = ContentType.objects.get_for_model(instance)
        changed_object_id = instance.id

        # Generate a unique identifier for this change to stash in the change context
        # This is used for deferred change logging and for looking up related changes without querying the database
        unique_object_change_id = None
        if user is not None:
            unique_object_change_id = f"{changed_object_type.pk}__{changed_object_id}__{user.pk}"
        else:
            unique_object_change_id = f"{changed_object_type.pk}__{changed_object_id}"

        # If a change already exists for this change_id, user, and object, update it instead of creating a new one.
        # If the object was deleted then recreated with the same pk (don't do this), change the action to update.
        if unique_object_change_id in change_context.deferred_object_changes:
            related_changes = ObjectChange.objects.filter(
                changed_object_type=changed_object_type,
                changed_object_id=changed_object_id,
                user=user,
                request_id=change_context.change_id,
            )

            # Skip the database check when deferring object changes
            if not change_context.defer_object_changes and related_changes.exists():
                objectchange = instance.to_objectchange(action)
                if objectchange is not None:
                    most_recent_change = related_changes.order_by("-time").first()
                    if most_recent_change.action == ObjectChangeActionChoices.ACTION_DELETE:
                        most_recent_change.action = ObjectChangeActionChoices.ACTION_UPDATE
                    most_recent_change.object_data = objectchange.object_data
                    most_recent_change.object_data_v2 = objectchange.object_data_v2
                    most_recent_change.save()

        else:
            change_context.deferred_object_changes[unique_object_change_id] = [
                {"action": action, "instance": instance, "user": user}
            ]
            if not change_context.defer_object_changes:
                objectchange = instance.to_objectchange(action)
                if objectchange is not None:
                    objectchange.user = user
                    objectchange.request_id = change_context.change_id
                    objectchange.change_context = change_context.context
                    objectchange.change_context_detail = change_context.context_detail[
                        :CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL
                    ]
                    objectchange.save()

        # restore field cache
        instance._state.fields_cache = original_cache

    # Increment metric counters
    if action == ObjectChangeActionChoices.ACTION_CREATE:
        model_inserts.labels(instance._meta.model_name).inc()
    elif action == ObjectChangeActionChoices.ACTION_UPDATE:
        model_updates.labels(instance._meta.model_name).inc()


@receiver(pre_delete)
def _handle_deleted_object(sender, instance, **kwargs):
    """
    Fires when an object is deleted.
    """
    change_context = change_context_state.get()

    if change_context is None:
        return

    if isinstance(instance, BaseModel):
        associations = ContactAssociation.objects.filter(
            associated_object_type=ContentType.objects.get_for_model(type(instance)), associated_object_id=instance.pk
        )
        associations.delete()

    if hasattr(instance, "notes") and isinstance(instance.notes, NotesQuerySet):
        notes = instance.notes
        notes.delete()

    # Record an ObjectChange if applicable
    if hasattr(instance, "to_objectchange"):
        user = change_context.get_user(instance)

        # save a copy of this instance's field cache so it can be restored after serialization
        # to prevent unexpected behavior when chaining multiple signal handlers
        original_cache = instance._state.fields_cache.copy()

        changed_object_type = ContentType.objects.get_for_model(instance)
        changed_object_id = instance.id

        # Generate a unique identifier for this change to stash in the change context
        # This is used for deferred change logging and for looking up related changes without querying the database
        unique_object_change_id = f"{changed_object_type.pk}__{changed_object_id}__{user.pk}"
        save_new_objectchange = True

        # if a change already exists for this change_id, user, and object, update it instead of creating a new one
        # except in the case that the object was created and deleted in the same change_id
        # we don't want to create a delete change for an object that never existed
        if unique_object_change_id in change_context.deferred_object_changes:
            cached_related_change = change_context.deferred_object_changes[unique_object_change_id][-1]
            if cached_related_change["action"] != ObjectChangeActionChoices.ACTION_CREATE:
                cached_related_change["action"] = ObjectChangeActionChoices.ACTION_DELETE
                save_new_objectchange = False

            related_changes = ObjectChange.objects.filter(
                changed_object_type=changed_object_type,
                changed_object_id=changed_object_id,
                user=user,
                request_id=change_context.change_id,
            )

            # Skip the database check when deferring object changes
            if not change_context.defer_object_changes and related_changes.exists():
                objectchange = instance.to_objectchange(ObjectChangeActionChoices.ACTION_DELETE)
                if objectchange is not None:
                    most_recent_change = related_changes.order_by("-time").first()
                    if most_recent_change.action != ObjectChangeActionChoices.ACTION_CREATE:
                        most_recent_change.action = ObjectChangeActionChoices.ACTION_DELETE
                        most_recent_change.object_data = objectchange.object_data
                        most_recent_change.object_data_v2 = objectchange.object_data_v2
                        most_recent_change.save()
                        save_new_objectchange = False

        if save_new_objectchange:
            change_context.deferred_object_changes.setdefault(unique_object_change_id, []).append(
                {
                    "action": ObjectChangeActionChoices.ACTION_DELETE,
                    "instance": instance,
                    "user": user,
                    "changed_object_id": changed_object_id,
                    "changed_object_type": changed_object_type,
                }
            )
            if not change_context.defer_object_changes:
                objectchange = instance.to_objectchange(ObjectChangeActionChoices.ACTION_DELETE)
                if objectchange is not None:
                    objectchange.user = user
                    objectchange.request_id = change_context.change_id
                    objectchange.change_context = change_context.context
                    objectchange.change_context_detail = change_context.context_detail[
                        :CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL
                    ]
                    objectchange.save()

        # restore field cache
        instance._state.fields_cache = original_cache

    # Increment metric counters
    model_deletes.labels(instance._meta.model_name).inc()


#
# Content types
#


@receiver(post_migrate)
def post_migrate_clear_content_type_caches(sender, app_config, signal, **kwargs):
    """Clear various content-type caches after a migration."""
    with contextlib.suppress(redis.exceptions.ConnectionError):
        cache.delete("nautobot.extras.utils.change_logged_models_queryset")
        cache.delete_pattern("nautobot.extras.utils.FeatureQuery.*")


#
# Custom fields
#


def handle_cf_removed_obj_types(instance, action, pk_set, **kwargs):
    """
    Handle the cleanup of old custom field data when a CustomField is removed from one or more ContentTypes.
    """

    change_context = change_context_state.get()
    if change_context is None:
        context = None
    else:
        context = change_context.as_dict(instance=instance)
    if action == "post_remove":
        # Existing content types have been removed from the custom field, delete their data
        if context:
            context["context_detail"] = "delete custom field data from existing content types"
        transaction.on_commit(lambda: delete_custom_field_data.delay(instance.key, pk_set, context))

    elif action == "post_add":
        # New content types have been added to the custom field, provision them
        if context:
            context["context_detail"] = "provision custom field data for new content types"
        transaction.on_commit(lambda: provision_field.delay(instance.pk, pk_set, context))


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

    try:
        refresh_datasource_content("extras.gitrepository", instance, None, job_result, delete=True)

        # In a distributed Nautobot deployment, each Django instance and/or worker instance may have its own clone
        # of this repository; we need some way to ensure that all such clones are deleted.
        # In the Celery worker case, we can broadcast a control message to all workers to do so:
        app.control.broadcast("discard_git_repository", repository_slug=instance.slug)
        # But we don't have an equivalent way to broadcast to any other Django instances.
        # For now we just delete the one that we have locally and rely on other methods,
        # such as the import_jobs() signal that runs on server startup,
        # to clean up other clones as they're encountered.
        if os.path.isdir(instance.filesystem_path):
            shutil.rmtree(instance.filesystem_path)
    except Exception as exc:
        job_result.result = {
            "exc_type": type(exc).__name__,
            "exc_message": sanitize(str(exc)),
        }
        job_result.status = JobResultStatusChoices.STATUS_FAILURE
        job_result.traceback = sanitize("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    else:
        job_result.status = JobResultStatusChoices.STATUS_SUCCESS
    finally:
        job_result.date_done = timezone.now()
        job_result.save()


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


def dynamic_group_update_cached_members(sender, instance, **kwargs):
    """
    When a DynamicGroup or DynamicGroupMembership is updated, update the cache of members for it and any parent groups.
    """
    if isinstance(instance, DynamicGroupMembership):
        group = instance.parent_group
    else:
        group = instance

    group.update_cached_members()
    for ancestor in group.get_ancestors():
        ancestor.update_cached_members()


post_save.connect(dynamic_group_update_cached_members, sender=DynamicGroup)
post_save.connect(dynamic_group_update_cached_members, sender=DynamicGroupMembership)


#
# Jobs
#


@receiver(pre_delete, sender=JobResult)
def job_result_delete_associated_files(instance, **kwargs):
    """For each related FileProxy, make sure its file gets deleted correctly from disk or database."""
    if get_storage_class(settings.JOB_FILE_IO_STORAGE) == DatabaseFileStorage:
        for file_proxy in instance.files.all():
            delete_file(file_proxy, "file")
    else:
        for file_proxy in instance.files.all():
            file_proxy.file.delete()


def refresh_job_models(sender, *, apps, **kwargs):
    """
    Callback for the nautobot_database_ready signal; updates Jobs in the database based on Job source file availability.
    """
    from nautobot.extras.jobs import get_jobs  # avoid circular import

    Job = apps.get_model("extras", "Job")

    # To make reverse migrations safe
    if not hasattr(Job, "job_class_name"):
        logger.info("Skipping refresh_job_models() as it appears Job model has not yet been migrated to latest.")
        return

    import_jobs()

    job_models = []

    for job_class in get_jobs().values():
        job_model, _ = refresh_job_model_from_job_class(Job, job_class)
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


#
# Metadata
#


def handle_mdt_removed_obj_types(instance, action, pk_set, **kwargs):  # pylint: disable=useless-return
    """Handle the cleanup of old Metadata when a MetadataType is removed from one or more ContentTypes."""
    if action != "post_remove":
        return
    # Existing content types have been removed from the MetadataType, delete their data.
    # TODO delete Metadata records with object_type in pk_set and metadata_type == instance


m2m_changed.connect(handle_mdt_removed_obj_types, sender=MetadataType.content_types.through)
