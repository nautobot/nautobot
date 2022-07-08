import uuid
from contextlib import contextmanager

from django.contrib.auth import get_user_model
from django.db.models.signals import m2m_changed, pre_delete, post_save

from nautobot.extras.choices import ObjectChangeEventContextChoices
from nautobot.extras.signals import _handle_changed_object, _handle_deleted_object
from nautobot.utilities.utils import curry


class ChangeContext(object):
    def __init__(self, user, context=None, context_detail="", id=None):
        self.context_detail = context_detail
        self.user = user
        if context is not None:
            self.context = context

        # Assign a random unique ID. This will be used to associate multiple object changes made during the same request.
        self.id = id
        if self.id is None:
            self.id = uuid.uuid4()


class JobChangeContext(ChangeContext):
    """ChangeContext for Jobs"""

    context = ObjectChangeEventContextChoices.CONTEXT_JOB


class ORMChangeContext(ChangeContext):
    """ChangeContext for changes made with web_request_context context manager"""

    context = ObjectChangeEventContextChoices.CONTEXT_ORM


class WebChangeContext(ChangeContext):
    """ChangeContext for changes made through the Web UI"""

    context = ObjectChangeEventContextChoices.CONTEXT_WEB


@contextmanager
def change_logging(change_context):
    """
    Enable change logging by connecting the appropriate signals to their receivers before code is run, and
    disconnecting them afterward.

    :param change_context: ChangeContext object with a unique `id` set
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
def web_request_context(user):
    """
    Emulate the context of an HTTP request, which provides functions like change logging and webhook processing
    in response to data changes. This context manager is for use with low level utility tooling, such as the
    nbshell management command. By default, when working with the Django ORM, neither change logging nor webhook
    processing occur unless manually invoked and this context manager handles those functions. A User object must be
    provided and a WSGIRequest request object may optionally be passed. If not provided, the request object will
    be created automatically.

    Example usage:

    >>> from nautobot.extras.context_managers import web_request_context
    >>> user = User.objects.get(username="admin")
    >>> with web_request_context(user):
    ...     lax = Site(name="LAX")
    ...     lax.validated_save()

    :param user: User object
    """

    if not isinstance(user, get_user_model()):
        raise TypeError("The user object must be an instance of nautobot.users.models.User")

    change_context = ORMChangeContext(user)
    with change_logging(change_context):
        yield
