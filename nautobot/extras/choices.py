from nautobot.utilities.choices import ChoiceSet


#
# Banners (currently plugin-specific)
#


class BannerClassChoices(ChoiceSet):
    """Styling choices for custom banners."""

    CLASS_SUCCESS = "success"
    CLASS_INFO = "info"
    CLASS_WARNING = "warning"
    CLASS_DANGER = "danger"

    CHOICES = (
        (CLASS_SUCCESS, "Success"),
        (CLASS_INFO, "Info"),
        (CLASS_WARNING, "Warning"),
        (CLASS_DANGER, "Danger"),
    )


#
# CustomFields
#


class CustomFieldFilterLogicChoices(ChoiceSet):

    FILTER_DISABLED = "disabled"
    FILTER_LOOSE = "loose"
    FILTER_EXACT = "exact"

    CHOICES = (
        (FILTER_DISABLED, "Disabled"),
        (FILTER_LOOSE, "Loose"),
        (FILTER_EXACT, "Exact"),
    )


class CustomFieldTypeChoices(ChoiceSet):

    TYPE_TEXT = "text"
    TYPE_INTEGER = "integer"
    TYPE_BOOLEAN = "boolean"
    TYPE_DATE = "date"
    TYPE_URL = "url"
    TYPE_SELECT = "select"
    TYPE_MULTISELECT = "multi-select"
    TYPE_JSON = "json"

    CHOICES = (
        (TYPE_TEXT, "Text"),
        (TYPE_INTEGER, "Integer"),
        (TYPE_BOOLEAN, "Boolean (true/false)"),
        (TYPE_DATE, "Date"),
        (TYPE_URL, "URL"),
        (TYPE_SELECT, "Selection"),
        (TYPE_MULTISELECT, "Multiple selection"),
        (TYPE_JSON, "JSON"),
    )

    REGEX_TYPES = (
        TYPE_TEXT,
        TYPE_URL,
        TYPE_SELECT,
        TYPE_MULTISELECT,
    )


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
# Dynamic Groups
#


class DynamicGroupOperatorChoices(ChoiceSet):
    OPERATOR_UNION = "union"
    OPERATOR_INTERSECTION = "intersection"
    OPERATOR_DIFFERENCE = "difference"

    CHOICES = (
        (OPERATOR_UNION, "Include (OR)"),
        (OPERATOR_INTERSECTION, "Restrict (AND)"),
        (OPERATOR_DIFFERENCE, "Exclude (NOT)"),
    )


#
# Jobs
#


class JobSourceChoices(ChoiceSet):

    SOURCE_LOCAL = "local"
    SOURCE_GIT = "git"
    SOURCE_PLUGIN = "plugins"

    CHOICES = (
        (SOURCE_LOCAL, "Installed in $JOBS_ROOT"),
        (SOURCE_GIT, "Provided by a Git repository"),
        (SOURCE_PLUGIN, "Part of a plugin"),
    )


class JobExecutionType(ChoiceSet):

    TYPE_IMMEDIATELY = "immediately"
    TYPE_FUTURE = "future"
    TYPE_HOURLY = "hourly"
    TYPE_DAILY = "daily"
    TYPE_WEEKLY = "weekly"
    TYPE_CUSTOM = "custom"

    CHOICES = (
        (TYPE_IMMEDIATELY, "Once immediately"),
        (TYPE_FUTURE, "Once in the future"),
        (TYPE_HOURLY, "Recurring hourly"),
        (TYPE_DAILY, "Recurring daily"),
        (TYPE_WEEKLY, "Recurring weekly"),
        (TYPE_CUSTOM, "Recurring custom"),
    )

    SCHEDULE_CHOICES = (
        TYPE_FUTURE,
        TYPE_HOURLY,
        TYPE_DAILY,
        TYPE_WEEKLY,
        TYPE_CUSTOM,
    )

    RECURRING_CHOICES = (
        TYPE_HOURLY,
        TYPE_DAILY,
        TYPE_WEEKLY,
        TYPE_CUSTOM,
    )

    CELERY_INTERVAL_MAP = {
        TYPE_HOURLY: "hours",
        TYPE_DAILY: "days",
        TYPE_WEEKLY: "days",  # a week is expressed as 7 days
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


class ObjectChangeEventContextChoices(ChoiceSet):

    CONTEXT_WEB = "web"
    CONTEXT_JOB = "job"
    CONTEXT_JOB_HOOK = "job-hook"
    CONTEXT_ORM = "orm"
    CONTEXT_UNKNOWN = "unknown"

    CHOICES = (
        (CONTEXT_WEB, "Web"),
        (CONTEXT_JOB, "Job"),
        (CONTEXT_JOB_HOOK, "Job hook"),
        (CONTEXT_ORM, "ORM"),
        (CONTEXT_UNKNOWN, "Unknown"),
    )


#
# Relationships
#


class RelationshipRequiredSideChoices(ChoiceSet):
    NEITHER_SIDE_REQUIRED = ""
    SOURCE_SIDE_REQUIRED = "source"
    DESTINATION_SIDE_REQUIRED = "destination"

    CHOICES = (
        (NEITHER_SIDE_REQUIRED, "Neither side required"),
        (SOURCE_SIDE_REQUIRED, "Source objects MUST implement this relationship"),
        (DESTINATION_SIDE_REQUIRED, "Destination objects MUST implement this relationship"),
    )


class RelationshipSideChoices(ChoiceSet):

    SIDE_SOURCE = "source"
    SIDE_DESTINATION = "destination"
    SIDE_PEER = "peer"  # for symmetric / non-directional relationships

    CHOICES = (
        (SIDE_SOURCE, "Source"),
        (SIDE_DESTINATION, "Destination"),
        (SIDE_PEER, "Peer"),
    )

    OPPOSITE = {
        SIDE_SOURCE: SIDE_DESTINATION,
        SIDE_DESTINATION: SIDE_SOURCE,
        SIDE_PEER: SIDE_PEER,
    }


class RelationshipTypeChoices(ChoiceSet):

    TYPE_ONE_TO_ONE = "one-to-one"
    TYPE_ONE_TO_ONE_SYMMETRIC = "symmetric-one-to-one"
    TYPE_ONE_TO_MANY = "one-to-many"
    TYPE_MANY_TO_MANY = "many-to-many"
    TYPE_MANY_TO_MANY_SYMMETRIC = "symmetric-many-to-many"

    CHOICES = (
        (TYPE_ONE_TO_ONE, "One to One"),
        (TYPE_ONE_TO_ONE_SYMMETRIC, "Symmetric One to One"),
        (TYPE_ONE_TO_MANY, "One to Many"),
        (TYPE_MANY_TO_MANY, "Many to Many"),
        (TYPE_MANY_TO_MANY_SYMMETRIC, "Symmetric Many to Many"),
    )


#
# Secrets
#


class SecretsGroupAccessTypeChoices(ChoiceSet):

    TYPE_GENERIC = "Generic"

    TYPE_CONSOLE = "Console"
    TYPE_GNMI = "gNMI"
    TYPE_HTTP = "HTTP(S)"
    TYPE_NETCONF = "NETCONF"
    TYPE_REST = "REST"
    TYPE_RESTCONF = "RESTCONF"
    TYPE_SNMP = "SNMP"
    TYPE_SSH = "SSH"

    CHOICES = (
        (TYPE_GENERIC, "Generic"),
        (TYPE_CONSOLE, "Console"),
        (TYPE_GNMI, "gNMI"),
        (TYPE_HTTP, "HTTP(S)"),
        (TYPE_NETCONF, "NETCONF"),
        (TYPE_REST, "REST"),
        (TYPE_RESTCONF, "RESTCONF"),
        (TYPE_SNMP, "SNMP"),
        (TYPE_SSH, "SSH"),
    )


class SecretsGroupSecretTypeChoices(ChoiceSet):

    TYPE_KEY = "key"
    TYPE_PASSWORD = "password"
    TYPE_SECRET = "secret"
    TYPE_TOKEN = "token"
    TYPE_USERNAME = "username"

    CHOICES = (
        (TYPE_KEY, "Key"),
        (TYPE_PASSWORD, "Password"),
        (TYPE_SECRET, "Secret"),
        (TYPE_TOKEN, "Token"),
        (TYPE_USERNAME, "Username"),
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
