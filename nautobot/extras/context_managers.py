import uuid
from contextlib import contextmanager

from django.contrib.auth import get_user_model
from django.db.models.signals import m2m_changed, pre_delete, post_save

from nautobot.extras.choices import ObjectChangeEventContextChoices
from nautobot.extras.signals import _handle_changed_object, _handle_deleted_object
from nautobot.utilities.utils import curry


class ChangeContext:
    """
    ChangeContext is used to describe a single transaction that may be related
    to one or more object changes. A unique id can be provided, otherwise
    one will be generated to relate any changes to this transaction. Convenience
    classes are provided for each context.

    :param user: User object
    :param context: Context of the transaction, must match a choice in nautobot.extras.choices.ObjectChangeEventContextChoices
    :param context_detail: Optional extra details about the transaction (ex: the plugin name that initiated the change)
    :param id: Optional uuid object to uniquely identify the transaction
    """

    def __init__(self, user, context=None, context_detail="", id=None):
        self.user = user

        if context is not None:
            self.context = context
        if self.context not in ObjectChangeEventContextChoices.values():
            raise ValueError("Context must be a choice within ObjectChangeEventContextChoices")

        self.context_detail = context_detail

        self.id = id
        if self.id is None:
            self.id = uuid.uuid4()


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
def change_logging(change_context):
    """
    Enable change logging by connecting the appropriate signals to their receivers before code is run, and
    disconnecting them afterward.

    :param change_context: ChangeContext instance
    """
    # Curry signals receivers to pass the current request
    handle_changed_object = curry(_handle_changed_object, change_context)
    handle_deleted_object = curry(_handle_deleted_object, change_context)

    # Connect our receivers to the post_save and post_delete signals.
    post_save.connect(handle_changed_object, dispatch_uid="handle_changed_object")
    m2m_changed.connect(handle_changed_object, dispatch_uid="handle_changed_object")
    pre_delete.connect(handle_deleted_object, dispatch_uid="handle_deleted_object")

    yield

    # Disconnect change logging signals. This is necessary to avoid recording any errant
    # changes during test cleanup.
    post_save.disconnect(handle_changed_object, dispatch_uid="handle_changed_object")
    m2m_changed.disconnect(handle_changed_object, dispatch_uid="handle_changed_object")
    pre_delete.disconnect(handle_deleted_object, dispatch_uid="handle_deleted_object")


@contextmanager
def web_request_context(user, context_detail=""):
    """
    Emulate the context of an HTTP request, which provides functions like change logging and webhook processing
    in response to data changes. This context manager is for use with low level utility tooling, such as the
    nbshell management command. By default, when working with the Django ORM, neither change logging nor webhook
    processing occur unless manually invoked and this context manager handles those functions. A valid User object
    must be provided.

    Example usage:

    >>> from nautobot.extras.context_managers import web_request_context
    >>> user = User.objects.get(username="admin")
    >>> with web_request_context(user, "manual-fix"):
    ...     lax = Site(name="LAX")
    ...     lax.validated_save()

    :param user: User object
    :param context_detail: Optional extra details about the transaction (ex: the plugin name that initiated the change)
    """

    if not isinstance(user, get_user_model()):
        raise TypeError("The user object must be an instance of nautobot.users.models.User")

    change_context = ORMChangeContext(user, context_detail=context_detail)
    with change_logging(change_context):
        yield
