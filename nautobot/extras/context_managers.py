import uuid
from contextlib import contextmanager

from django.contrib.auth import get_user_model
from django.test.client import RequestFactory

from nautobot.extras.choices import ObjectChangeEventContextChoices
from nautobot.extras.signals import change_context_state


class ChangeContext:
    """
    ChangeContext is used to describe a single transaction that may be related
    to one or more object changes. A unique id can be provided, otherwise
    one will be generated to relate any changes to this transaction. Convenience
    classes are provided for each context.

    :param user: User object
    :param request: WSGIRequest object to retrieve user from django rest framework after authentication is performed
    :param context: Context of the transaction, must match a choice in nautobot.extras.choices.ObjectChangeEventContextChoices
    :param context_detail: Optional extra details about the transaction (ex: the plugin name that initiated the change)
    :param change_id: Optional uuid object to uniquely identify the transaction. One will be generated if not supplied
    """

    def __init__(self, user=None, request=None, context=None, context_detail="", change_id=None):
        self.request = request
        self.user = user

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

    def get_user(self):
        """Return self.user if set, otherwise return self.request.user"""
        if self.user is not None:
            return self.user
        return self.request.user


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

    # Set change logging state
    prev_state = change_context_state.set(change_context)

    try:
        yield
    finally:
        # Reset change logging state. This is necessary to avoid recording any errant
        # changes during test cleanup.
        change_context_state.reset(prev_state)


@contextmanager
def web_request_context(user, context_detail="", change_id=None):
    """
    Emulate the context of an HTTP request, which provides functions like change logging and webhook processing
    in response to data changes. This context manager is for use with low level utility tooling, such as the
    'nautobot-server nbshell' management command.

    By default, when working with the Django ORM, neither change logging nor webhook processing occur
    unless manually invoked and this context manager handles those functions. A valid User object must be provided.

    Example usage:

    >>> from nautobot.extras.context_managers import web_request_context
    >>> user = User.objects.get(username="admin")
    >>> with web_request_context(user, context_detail="manual-fix"):
    ...     lt = Location.objects.get(name="Root")
    ...     lax = Location(name="LAX", location_type=lt)
    ...     lax.validated_save()

    :param user: User object
    :param context_detail: Optional extra details about the transaction (ex: the plugin name that initiated the change)
    :param change_id: Optional uuid object to uniquely identify the transaction. One will be generated if not supplied
    """

    if not isinstance(user, get_user_model()):
        raise TypeError("The user object must be an instance of nautobot.users.models.User")

    request = RequestFactory().request(SERVER_NAME="web_request_context")
    request.user = user
    change_context = ORMChangeContext(request=request, context_detail=context_detail, change_id=change_id)
    with change_logging(change_context):
        yield request
