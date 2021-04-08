from nautobot.utilities.choices import ChoiceSet


#
# CustomFields
#


class CustomFieldTypeChoices(ChoiceSet):

    TYPE_TEXT = "text"
    TYPE_INTEGER = "integer"
    TYPE_BOOLEAN = "boolean"
    TYPE_DATE = "date"
    TYPE_URL = "url"
    TYPE_SELECT = "select"
    TYPE_MULTISELECT = "multi-select"

    CHOICES = (
        (TYPE_TEXT, "Text"),
        (TYPE_INTEGER, "Integer"),
        (TYPE_BOOLEAN, "Boolean (true/false)"),
        (TYPE_DATE, "Date"),
        (TYPE_URL, "URL"),
        (TYPE_SELECT, "Selection"),
        (TYPE_MULTISELECT, "Multiple selection"),
    )


class CustomFieldFilterLogicChoices(ChoiceSet):

    FILTER_DISABLED = "disabled"
    FILTER_LOOSE = "loose"
    FILTER_EXACT = "exact"

    CHOICES = (
        (FILTER_DISABLED, "Disabled"),
        (FILTER_LOOSE, "Loose"),
        (FILTER_EXACT, "Exact"),
    )


#
# Relationships
#


class RelationshipTypeChoices(ChoiceSet):

    TYPE_ONE_TO_ONE = "one-to-one"
    TYPE_ONE_TO_MANY = "one-to-many"
    TYPE_MANY_TO_MANY = "many-to-many"

    CHOICES = (
        (TYPE_ONE_TO_ONE, "One to One"),
        (TYPE_ONE_TO_MANY, "One to Many"),
        (TYPE_MANY_TO_MANY, "Many to Many"),
    )


class RelationshipSideChoices(ChoiceSet):

    SIDE_SOURCE = "source"
    SIDE_DESTINATION = "destination"

    CHOICES = (
        (SIDE_SOURCE, "Source"),
        (SIDE_DESTINATION, "Destination"),
    )

    OPPOSITE = {SIDE_SOURCE: SIDE_DESTINATION, SIDE_DESTINATION: SIDE_SOURCE}


#
# CustomLinks
#


class CustomLinkButtonClassChoices(ChoiceSet):

    CLASS_DEFAULT = "default"
    CLASS_PRIMARY = "primary"
    CLASS_SUCCESS = "success"
    CLASS_INFO = "info"
    CLASS_WARNING = "warning"
    CLASS_DANGER = "danger"
    CLASS_LINK = "link"

    CHOICES = (
        (CLASS_DEFAULT, "Default"),
        (CLASS_PRIMARY, "Primary (blue)"),
        (CLASS_SUCCESS, "Success (green)"),
        (CLASS_INFO, "Info (aqua)"),
        (CLASS_WARNING, "Warning (orange)"),
        (CLASS_DANGER, "Danger (red)"),
        (CLASS_LINK, "None (link)"),
    )


#
# ObjectChanges
#


class ObjectChangeActionChoices(ChoiceSet):

    ACTION_CREATE = "create"
    ACTION_UPDATE = "update"
    ACTION_DELETE = "delete"

    CHOICES = (
        (ACTION_CREATE, "Created"),
        (ACTION_UPDATE, "Updated"),
        (ACTION_DELETE, "Deleted"),
    )

    CSS_CLASSES = {
        ACTION_CREATE: "success",
        ACTION_UPDATE: "primary",
        ACTION_DELETE: "danger",
    }


#
# Log Levels for Jobs (formerly Reports and Custom Scripts)
#


class LogLevelChoices(ChoiceSet):

    LOG_DEFAULT = "default"
    LOG_SUCCESS = "success"
    LOG_INFO = "info"
    LOG_WARNING = "warning"
    LOG_FAILURE = "failure"

    CHOICES = (
        (LOG_DEFAULT, "Default"),
        (LOG_SUCCESS, "Success"),
        (LOG_INFO, "Info"),
        (LOG_WARNING, "Warning"),
        (LOG_FAILURE, "Failure"),
    )

    CSS_CLASSES = {
        LOG_DEFAULT: "default",
        LOG_SUCCESS: "success",
        LOG_INFO: "info",
        LOG_WARNING: "warning",
        LOG_FAILURE: "danger",
    }


#
# Job results
#


class JobResultStatusChoices(ChoiceSet):

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_ERRORED = "errored"
    STATUS_FAILED = "failed"

    CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_ERRORED, "Errored"),
        (STATUS_FAILED, "Failed"),
    )

    TERMINAL_STATE_CHOICES = (
        STATUS_COMPLETED,
        STATUS_ERRORED,
        STATUS_FAILED,
    )


#
# Webhooks
#


class WebhookHttpMethodChoices(ChoiceSet):

    METHOD_GET = "GET"
    METHOD_POST = "POST"
    METHOD_PUT = "PUT"
    METHOD_PATCH = "PATCH"
    METHOD_DELETE = "DELETE"

    CHOICES = (
        (METHOD_GET, "GET"),
        (METHOD_POST, "POST"),
        (METHOD_PUT, "PUT"),
        (METHOD_PATCH, "PATCH"),
        (METHOD_DELETE, "DELETE"),
    )
