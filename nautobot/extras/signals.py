import os
import random
import shutil
import uuid
import logging
from datetime import timedelta

from cacheops.signals import cache_invalidated, cache_read
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models.signals import m2m_changed, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from django_prometheus.models import model_deletes, model_inserts, model_updates
from prometheus_client import Counter

from nautobot.extras.tasks import delete_custom_field_data, provision_field
from .choices import JobResultStatusChoices, ObjectChangeActionChoices
from .models import CustomField, GitRepository, JobResult, ObjectChange
from .webhooks import enqueue_webhooks

logger = logging.getLogger("nautobot.extras.signals")


#
# Change logging/webhooks
#


def _get_user_if_authenticated(request, objectchange):
    """Return the user object associated with the request if the user is defined.

    If the user is not defined, log a warning to indicate that the user couldn't be retrived from the request
    This is a workaround to fix a recurring issue where the user shouldn't be present in the request object randomly.
    A similar issue was reported in NetBox https://github.com/netbox-community/netbox/issues/5142
    """
    if request.user.is_authenticated:
        return request.user
    else:
        logger.warning(f"Unable to retrieve the user while creating the changelog for {objectchange.changed_object}")


def _handle_changed_object(request, sender, instance, **kwargs):
    """
    Fires when an object is created or updated.
    """
    # Queue the object for processing once the request completes
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
        objectchange = instance.to_objectchange(action)
        objectchange.user = _get_user_if_authenticated(request, objectchange)
        objectchange.request_id = request.id
        objectchange.save()

    # Enqueue webhooks
    enqueue_webhooks(instance, request.user, request.id, action)

    # Increment metric counters
    if action == ObjectChangeActionChoices.ACTION_CREATE:
        model_inserts.labels(instance._meta.model_name).inc()
    elif action == ObjectChangeActionChoices.ACTION_UPDATE:
        model_updates.labels(instance._meta.model_name).inc()

    # Housekeeping: 0.1% chance of clearing out expired ObjectChanges
    if settings.CHANGELOG_RETENTION and random.randint(1, 1000) == 1:
        cutoff = timezone.now() - timedelta(days=settings.CHANGELOG_RETENTION)
        ObjectChange.objects.filter(time__lt=cutoff).delete()


def _handle_deleted_object(request, sender, instance, **kwargs):
    """
    Fires when an object is deleted.
    """
    # Record an ObjectChange if applicable
    if hasattr(instance, "to_objectchange"):
        objectchange = instance.to_objectchange(ObjectChangeActionChoices.ACTION_DELETE)
        objectchange.user = _get_user_if_authenticated(request, objectchange)
        objectchange.request_id = request.id
        objectchange.save()

    # Enqueue webhooks
    enqueue_webhooks(instance, request.user, request.id, ObjectChangeActionChoices.ACTION_DELETE)

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

    refresh_datasource_content("extras.gitrepository", instance, None, job_result, delete=True)

    if job_result.status not in JobResultStatusChoices.TERMINAL_STATE_CHOICES:
        job_result.set_status(JobResultStatusChoices.STATUS_COMPLETED)
    job_result.save()

    # TODO: In a distributed Nautobot deployment, each Django instance and/or RQ worker instance may have its own clone
    # of this repository; we need some way to ensure that all such clones are deleted.
    # For now we just delete the one that we have locally and rely on other methods (notably get_jobs())
    # to clean up other clones as they're encountered.
    if os.path.isdir(instance.filesystem_path):
        shutil.rmtree(instance.filesystem_path)
