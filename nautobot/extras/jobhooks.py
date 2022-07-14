from django.utils.functional import classproperty

from .jobs import Job, ObjectVar

from nautobot.extras.models import ObjectChange

#
# JobHookReceiver
#


class JobHookReceiver(Job):
    """
    Base model for job hook receivers.
    """

    object_change = ObjectVar(model=ObjectChange)

    @classproperty
    def hidden(cls):
        return getattr(cls.Meta, "hidden", True)
