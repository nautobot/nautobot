from django.contrib.admin.models import ADDITION, CHANGE, DELETION

from nautobot.core.choices import ChoiceSet


class LogEntryActionFlagChoices(ChoiceSet):
    """Choices for Django admin LogEntry action flags."""

    CHOICES = (
        (ADDITION, "Addition"),
        (CHANGE, "Change"),
        (DELETION, "Deletion"),
    )


class LogEntryActionFlagClassChoices(ChoiceSet):
    """
    Mapping of Django admin action flags to Bootstrap badge color classes.
    """

    ADDITION_CLASS = "success"
    CHANGE_CLASS = "warning"
    DELETION_CLASS = "danger"
    DEFAULT_CLASS = "secondary"

    CHOICES = (
        (ADDITION, ADDITION_CLASS),
        (CHANGE, CHANGE_CLASS),
        (DELETION, DELETION_CLASS),
    )

    CSS_CLASSES = {
        ADDITION: ADDITION_CLASS,
        CHANGE: CHANGE_CLASS,
        DELETION: DELETION_CLASS,
    }

    @classmethod
    def get_class(cls, action_flag):
        return cls.CSS_CLASSES.get(action_flag, cls.DEFAULT_CLASS)
