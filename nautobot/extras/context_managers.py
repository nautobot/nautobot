from contextlib import contextmanager
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import transaction
from django.test.client import RequestFactory

from nautobot.core.events import publish_event
from nautobot.core.utils.otel import traced_span
from nautobot.extras.change_consumers import change_has_consumers, get_change_event_topic
from nautobot.extras.choices import ObjectChangeEventContextChoices
from nautobot.extras.conditions.gate import ConditionGate
from nautobot.extras.constants import CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL
from nautobot.extras.models import ObjectChange
from nautobot.extras.signals import change_context_state, get_user_if_authenticated
from nautobot.extras.webhooks import enqueue_webhooks


class ChangeContext:
    """
    ChangeContext is used to describe a single transaction that may be related
    to one or more object changes. A unique id can be provided, otherwise
    one will be generated to relate any changes to this transaction. Convenience
    classes are provided for each context.

    Args:
        user (User): User object
        request (WSGIRequest): object to retrieve user from django rest framework after authentication is performed
        context (ObjectChangeEventContextChoices): Context of the transaction
        context_detail (Optional[str]): extra details about the transaction (ex: plugin name that initiated the change)
        change_id (Optional[UUID]): Object to uniquely identify the transaction. One will be generated if not supplied

    The next two parameters hold the state of updated objects as the database held it before the save, keyed
    by primary key. `get_snapshots()` uses them as the `prechange` side of the diff. They are filled during
    the save itself, and only for objects whose changes have a consumer, since nothing else reads them.
    Only the v2 form is filled now. The v1 form stays for callers that supply their own data.

        pre_object_data (dict): Optional dictionary of serialized object data to be used in the object snapshot
        pre_object_data_v2 (dict): Optional dictionary of serialized object data to be used in the object snapshot
    """

    defer_object_changes = False  # advanced usage, for creating object changes in bulk

    def __init__(
        self,
        user=None,
        request=None,
        context=None,
        context_detail="",
        change_id=None,
        pre_object_data=None,
        pre_object_data_v2=None,
    ):
        self.request = request
        self.user = user
        self.reset_deferred_object_changes()

        if self.request is None and self.user is None:
            raise TypeError("Either user or request must be provided")

        if self.request is not None and self.user is not None:
            raise TypeError("Request and user cannot be used together")

        if context is not None:
            self.context = context
        if self.context not in ObjectChangeEventContextChoices.values():
            raise ValueError("Context must be a choice within ObjectChangeEventContextChoices")

        self.context_detail = context_detail

        self.change_id = change_id
        if self.change_id is None:
            self.change_id = uuid.uuid4()
        # A fresh dict per context. A shared default would carry one request's captures into the next.
        self.pre_object_data = {} if pre_object_data is None else pre_object_data
        self.pre_object_data_v2 = {} if pre_object_data_v2 is None else pre_object_data_v2
        self._consumers_by_type_and_action = {}

    def has_consumers(self, content_type, action):
        """Whether anything would act on a change with this content type and action.

        `change_has_consumers()` reads Redis, and outside a web request nothing memoizes that, so a job
        saving thousands of objects would ask for the same answer thousands of times. The answer is
        remembered here for the life of this context, which is one request or one job.

        Args:
            content_type (ContentType): Content type of the changed object.
            action (str): One of the `ObjectChangeActionChoices` values.

        Returns:
            (bool): True if at least one webhook, job hook, or event broker would be triggered.
        """
        key = (content_type.pk, action)
        if key not in self._consumers_by_type_and_action:
            self._consumers_by_type_and_action[key] = change_has_consumers(content_type, action)
        return self._consumers_by_type_and_action[key]

    def get_user(self, instance=None):
        """Return self.user if set, otherwise return self.request.user"""
        if self.user is not None:
            return get_user_if_authenticated(self.user, instance)
        return get_user_if_authenticated(self.request.user, instance)

    def as_dict(self, instance=None):
        """
        Return ChangeContext attributes in dictionary format
        """
        context = {
            "user": self.get_user(instance),
            "change_id": self.change_id,
            "context": self.context,
            "context_detail": self.context_detail,
            "pre_object_data": self.pre_object_data,
            "pre_object_data_v2": self.pre_object_data_v2,
        }
        return context

    def _object_change_batch(self, n):
        # Return first n keys from the self.deferred_object_changes dict
        keys = []
        for i, k in enumerate(self.deferred_object_changes.keys()):
            if i >= n:
                return keys
            keys.append(k)
        return keys

    def reset_deferred_object_changes(self):
        self.deferred_object_changes = {}

    def flush_deferred_object_changes(self, batch_size=1000):
        if self.defer_object_changes:
            self.create_object_changes(batch_size=batch_size)

    def create_object_changes(self, batch_size=1000):
        while self.deferred_object_changes:
            create_object_changes = []
            for key in self._object_change_batch(batch_size):
                for entry in self.deferred_object_changes[key]:
                    objectchange = entry["instance"].to_objectchange(entry["action"])
                    if objectchange is not None:
                        objectchange.user = entry["user"]
                        objectchange.user_name = objectchange.user.username
                        objectchange.request_id = self.change_id
                        objectchange.change_context = self.context
                        objectchange.change_context_detail = self.context_detail[:CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL]
                        if not objectchange.changed_object_id:  # changed_object was deleted
                            # Clear out the GenericForeignKey to keep Django from complaining about an unsaved object:
                            objectchange.changed_object = None
                            # Set the component fields individually:
                            objectchange.changed_object_id = entry.get("changed_object_id")
                            objectchange.changed_object_type = entry.get("changed_object_type")
                        create_object_changes.append(objectchange)
                self.deferred_object_changes.pop(key, None)
            ObjectChange.objects.bulk_create(create_object_changes, batch_size=batch_size)


class JobChangeContext(ChangeContext):
    """ChangeContext for changes made by jobs"""

    context = ObjectChangeEventContextChoices.CONTEXT_JOB


class JobHookChangeContext(ChangeContext):
    """ChangeContext for changes made by job hooks"""

    context = ObjectChangeEventContextChoices.CONTEXT_JOB_HOOK


class ORMChangeContext(ChangeContext):
    """ChangeContext for changes made with web_request_context context manager"""

    context = ObjectChangeEventContextChoices.CONTEXT_ORM


class WebChangeContext(ChangeContext):
    """ChangeContext for changes made through the web interface"""

    context = ObjectChangeEventContextChoices.CONTEXT_WEB


@contextmanager
def change_logging(change_context: ChangeContext):
    """
    Enable change logging by connecting the appropriate signals to their receivers before code is run, and
    disconnecting them afterward.
    """

    # Set change logging state
    prev_state = change_context_state.set(change_context)

    try:
        yield
    finally:
        # Reset change logging state. This is necessary to avoid recording any errant
        # changes during test cleanup.
        change_context_state.reset(prev_state)


@contextmanager
def web_request_context(
    user, context_detail="", change_id=None, context=ObjectChangeEventContextChoices.CONTEXT_ORM, request=None
):
    """
    Emulate the context of an HTTP request, which provides functions like change logging and webhook processing
    in response to data changes. This context manager is for use with low level utility tooling, such as the
    'nautobot-server nbshell' management command.

    By default, when working with the Django ORM, neither change logging nor webhook processing occur
    unless manually invoked and this context manager handles those functions. A valid User object must be provided.

    Examples:
        >>> from nautobot.extras.context_managers import web_request_context
        >>> user = User.objects.get(username="admin")
        >>> with web_request_context(user, context_detail="manual-fix"):
        ...     lt = Location.objects.get(name="Root")
        ...     lax = Location(name="LAX", location_type=lt)
        ...     lax.validated_save()

    Args:
        user (User): User object
        context_detail (str): Optional extra details about the transaction (ex: plugin name that initiated the change)
        change_id (Optional[UUID]): Object to uniquely identify the transaction. One will be generated if not supplied
        context (str): Optional string value of the generated change log entries' "change_context" field.
            Defaults to `ObjectChangeEventContextChoices.CONTEXT_ORM`.
            Valid choices are in `nautobot.extras.choices.ObjectChangeEventContextChoices`.
        request (Request): Optional web request instance, one will be generated if not supplied
    """
    from nautobot.extras.jobs import enqueue_job_hooks  # prevent circular import

    valid_contexts = {
        ObjectChangeEventContextChoices.CONTEXT_JOB: JobChangeContext,
        ObjectChangeEventContextChoices.CONTEXT_JOB_HOOK: JobHookChangeContext,
        ObjectChangeEventContextChoices.CONTEXT_ORM: ORMChangeContext,
        ObjectChangeEventContextChoices.CONTEXT_WEB: WebChangeContext,
    }

    if context not in valid_contexts:
        raise TypeError(f"{context} is not a valid context")

    if not isinstance(user, (get_user_model(), AnonymousUser)):
        raise TypeError(f"{user} is not a valid user object")

    if request is None:
        request = RequestFactory().request(SERVER_NAME="web_request_context")
        request.user = user
    change_context = valid_contexts[context](request=request, context_detail=context_detail, change_id=change_id)
    pre_object_data, pre_object_data_v2 = None, None
    try:
        with change_logging(change_context):
            yield request
            change_context = change_context_state.get()
            pre_object_data, pre_object_data_v2 = change_context.pre_object_data, change_context.pre_object_data_v2
    finally:
        jobs_reloaded = False
        # In bulk operations, we are performing the same action (create/update/delete) on the same content-type.
        # Save some repeated database queries by reusing the same evaluated querysets where applicable.
        jobhook_queryset = None
        webhook_queryset = None
        # One gate for the whole request, so a broken condition is reported once, not per object.
        condition_gate = ConditionGate()
        last_action = None
        last_content_type = None
        with traced_span(
            "nautobot.extras.changelog",
            "changelog.dispatch_hooks",
            **{
                "changelog.change_id": str(change_context.change_id),
                "changelog.context": context,
            },
        ) as _span:
            # enqueue jobhooks and webhooks, use change_context.change_id in case change_id was not supplied
            object_change_count = 0
            skipped_object_change_count = 0
            for oc in (
                ObjectChange.objects.select_related("changed_object_type", "user")
                .filter(request_id=change_context.change_id)
                .order_by("time")  # default ordering is -time but we want oldest first not newest first
                .defer("object_data", "object_data_v2")  # avoid an "Out of sort memory" exception on MySQL
                .iterator()
            ):
                # Counts every record written in this request, whether or not it is dispatched below.
                object_change_count += 1
                if oc.action != last_action or oc.changed_object_type != last_content_type:
                    jobhook_queryset = None
                    webhook_queryset = None
                last_action = oc.action
                last_content_type = oc.changed_object_type

                if not change_context.has_consumers(oc.changed_object_type, oc.action):
                    # Nothing is listening for this content type and action. No enabled webhook, no job
                    # hook, no event broker subscribed to the topic. For the same reason nothing captured
                    # a "before" state in pre_save, so get_snapshots() below would spend a query
                    # rebuilding one and then find nobody to send it to.
                    skipped_object_change_count += 1
                    continue

                # An update already had its "before" state captured in pre_save, so nothing is read here.
                # Deletes and M2M changes have no such capture and still pay a query for get_prev_change().
                # See https://github.com/nautobot/nautobot/issues/6303
                snapshots = oc.get_snapshots(
                    pre_object_data.get(str(oc.changed_object_id), None) if pre_object_data else None,
                    pre_object_data_v2.get(str(oc.changed_object_id), None) if pre_object_data_v2 else None,
                )

                if context != ObjectChangeEventContextChoices.CONTEXT_JOB_HOOK:
                    # Make sure JobHooks are up to date (only once) before calling them
                    did_reload_jobs, jobhook_queryset = enqueue_job_hooks(
                        oc,
                        may_reload_jobs=(not jobs_reloaded),
                        jobhook_queryset=jobhook_queryset,
                        snapshots=snapshots,
                        gate=condition_gate,
                    )
                    if did_reload_jobs:
                        jobs_reloaded = True

                webhook_queryset = enqueue_webhooks(
                    oc, snapshots=snapshots, webhook_queryset=webhook_queryset, gate=condition_gate
                )

                event_topic = get_change_event_topic(oc.changed_object_type, oc.action)
                event_payload = snapshots.copy()
                event_payload["context"] = {
                    "change_context": oc.get_change_context_display(),
                    "change_context_detail": oc.change_context_detail,
                    "request_id": str(oc.request_id),
                    "user_name": oc.user_name,
                    "timestamp": str(oc.time),
                }
                publish_event(topic=event_topic, payload=event_payload)

            _span.set_attribute("nautobot.extras.changelog.object_change_count", object_change_count)
            _span.set_attribute("nautobot.extras.changelog.skipped_object_change_count", skipped_object_change_count)


@contextmanager
def deferred_change_logging_for_bulk_operation():
    """
    Defers change logging until the end of the context manager to improve performance. For use with bulk edit views. This
    context manager is wrapped in an atomic transaction.
    """

    change_context = change_context_state.get()
    if change_context is None:
        raise ValueError("Change logging must be enabled before using deferred_change_logging_for_bulk_operation")

    with transaction.atomic():
        try:
            change_context.defer_object_changes = True
            yield
            change_context.flush_deferred_object_changes()
        finally:
            change_context.defer_object_changes = False
            change_context.reset_deferred_object_changes()
