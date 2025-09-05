from celery import states

from nautobot.core.choices import ChoiceSet
from nautobot.core.utils.deprecation import class_deprecated_in_favor_of

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
# Contact Association
#


class ContactAssociationRoleChoices(ChoiceSet):
    """Role choices for contact association instances"""

    ROLE_ADMINISTRATIVE = "administrative"
    ROLE_BILLING = "billing"
    ROLE_SUPPORT = "support"
    ROLE_ON_SITE = "on site"

    CHOICES = (
        (ROLE_ADMINISTRATIVE, "Administrative"),
        (ROLE_BILLING, "Billing"),
        (ROLE_SUPPORT, "Support"),
        (ROLE_ON_SITE, "On Site"),
    )


class ContactAssociationStatusChoices(ChoiceSet):
    """Status choices for contact association instances"""

    STATUS_PRIMARY = "primary"
    STATUS_SECONDARY = "secondary"
    STATUS_ACTIVE = "active"

    CHOICES = (
        (STATUS_PRIMARY, "Primary"),
        (STATUS_SECONDARY, "Secondary"),
        (STATUS_ACTIVE, "Active"),
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
    TYPE_MARKDOWN = "markdown"

    CHOICES = (
        (TYPE_TEXT, "Text"),
        (TYPE_INTEGER, "Integer"),
        (TYPE_BOOLEAN, "Boolean (true/false)"),
        (TYPE_DATE, "Date"),
        (TYPE_URL, "URL"),
        (TYPE_SELECT, "Selection"),
        (TYPE_MULTISELECT, "Multiple selection"),
        (TYPE_JSON, "JSON"),
        (TYPE_MARKDOWN, "Markdown"),
    )

    # Types that support validation_minimum/validation_maximum
    MIN_MAX_TYPES = (
        TYPE_TEXT,
        TYPE_INTEGER,
        TYPE_URL,
        TYPE_SELECT,
        TYPE_MULTISELECT,
        TYPE_JSON,
        TYPE_MARKDOWN,
    )

    # Types that support validation_regex
    REGEX_TYPES = (
        TYPE_TEXT,
        TYPE_URL,
        TYPE_SELECT,
        TYPE_MULTISELECT,
        TYPE_JSON,
        TYPE_MARKDOWN,
    )


#
# Button Classes
#


class ButtonClassChoices(ChoiceSet):
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
# CustomLinks
#


@class_deprecated_in_favor_of(ButtonClassChoices)
class CustomLinkButtonClassChoices(ButtonClassChoices):
    pass


#
# Dynamic Groups
#


class DynamicGroupTypeChoices(ChoiceSet):
    TYPE_DYNAMIC_FILTER = "dynamic-filter"
    TYPE_DYNAMIC_SET = "dynamic-set"
    TYPE_STATIC = "static"

    CHOICES = (
        (TYPE_DYNAMIC_FILTER, "Filter-defined"),
        (TYPE_DYNAMIC_SET, "Group of groups"),
        (TYPE_STATIC, "Static assignment"),
    )


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


class JobQueueTypeChoices(ChoiceSet):
    TYPE_CELERY = "celery"
    TYPE_KUBERNETES = "kubernetes"

    CHOICES = (
        (TYPE_CELERY, "Celery"),
        (TYPE_KUBERNETES, "Kubernetes"),
    )


#
# Job results
#


class JobResultStatusChoices(ChoiceSet):
    """
    These status choices are using the same taxonomy as within Celery core. A Nautobot Job status
    is equivalent to a Celery task state.
    """

    STATUS_FAILURE = states.FAILURE
    STATUS_IGNORED = states.IGNORED
    STATUS_PENDING = states.PENDING
    STATUS_RECEIVED = states.RECEIVED
    STATUS_REJECTED = states.REJECTED
    STATUS_RETRY = states.RETRY
    STATUS_REVOKED = states.REVOKED
    STATUS_STARTED = states.STARTED
    STATUS_SUCCESS = states.SUCCESS

    CHOICES = sorted(zip(states.ALL_STATES, states.ALL_STATES))

    #: Set of all possible states.
    ALL_STATES = states.ALL_STATES
    #: Set of states meaning the task returned an exception.
    EXCEPTION_STATES = states.EXCEPTION_STATES
    #: State precedence.
    #: None represents the precedence of an unknown state.
    #: Lower index means higher precedence.
    PRECEDENCE = states.PRECEDENCE
    #: Set of exception states that should propagate exceptions to the user.
    PROPAGATE_STATES = states.PROPAGATE_STATES
    #: Set of states meaning the task result is ready (has been executed).
    READY_STATES = states.READY_STATES
    #: Set of states meaning the task result is not ready (hasn't been executed).
    UNREADY_STATES = states.UNREADY_STATES

    @staticmethod
    def precedence(state):
        """
        Get the precedence for a state. Lower index means higher precedence.

        Args:
            state (str): One of the status choices.

        Returns:
            (int): Precedence value.

        Examples:
            >>> JobResultStatusChoices.precedence(JobResultStatusChoices.STATUS_SUCCESS)
            0

        """
        return states.precedence(state)


#
# Log Levels for Jobs (formerly Reports and Custom Scripts)
#


class LogLevelChoices(ChoiceSet):
    LOG_DEBUG = "debug"
    LOG_INFO = "info"
    LOG_SUCCESS = "success"
    LOG_WARNING = "warning"
    LOG_FAILURE = "failure"
    LOG_ERROR = "error"
    LOG_CRITICAL = "critical"

    CHOICES = (
        (LOG_DEBUG, "Debug"),
        (LOG_INFO, "Info"),
        (LOG_SUCCESS, "Success"),
        (LOG_WARNING, "Warning"),
        (LOG_FAILURE, "Failure"),
        (LOG_ERROR, "Error"),
        (LOG_CRITICAL, "Critical"),
    )

    CSS_CLASSES = {
        LOG_DEBUG: "debug",
        LOG_INFO: "info",
        LOG_SUCCESS: "success",
        LOG_WARNING: "warning",
        LOG_FAILURE: "failure",
        LOG_ERROR: "error",
        LOG_CRITICAL: "critical",
    }


#
# Metadata
#


class MetadataTypeDataTypeChoices(CustomFieldTypeChoices):
    """
    Values for the MetadataType.data_type field.

    Generally equivalent to CustomFieldTypeChoices, but adds TYPE_CONTACT_OR_TEAM.
    """

    TYPE_CONTACT_TEAM = "contact-or-team"
    # TODO: these should be migrated to CustomFieldTypeChoices and support added in CustomField data
    TYPE_DATETIME = "datetime"
    TYPE_FLOAT = "float"

    CHOICES = (
        *CustomFieldTypeChoices.CHOICES,
        (TYPE_CONTACT_TEAM, "Contact or Team"),
        # TODO: these should be migrated to CustomFieldTypeChoices and support added in CustomField data
        (TYPE_DATETIME, "Date/time"),
        (TYPE_FLOAT, "Floating point number"),
    )

    MIN_MAX_TYPES = (
        *CustomFieldTypeChoices.MIN_MAX_TYPES,
        TYPE_FLOAT,
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
    TYPE_AUTHKEY = "authentication-key"
    TYPE_AUTHPROTOCOL = "authentication-protocol"
    TYPE_KEY = "key"
    TYPE_NOTES = "notes"
    TYPE_PASSWORD = "password"  # noqa: S105  # hardcoded-password-string -- false positive
    TYPE_PRIVALGORITHM = "private-algorithm"
    TYPE_PRIVKEY = "private-key"
    TYPE_SECRET = "secret"  # noqa: S105  # hardcoded-password-string -- false positive
    TYPE_TOKEN = "token"  # noqa: S105  # hardcoded-password-string -- false positive
    TYPE_URL = "url"
    TYPE_USERNAME = "username"

    CHOICES = (
        (TYPE_AUTHKEY, "Authentication Key"),
        (TYPE_AUTHPROTOCOL, "Authentication Protocol"),
        (TYPE_KEY, "Key"),
        (TYPE_NOTES, "Notes"),
        (TYPE_PASSWORD, "Password"),
        (TYPE_PRIVALGORITHM, "Private Algorithm"),
        (TYPE_PRIVKEY, "Private Key"),
        (TYPE_SECRET, "Secret"),
        (TYPE_TOKEN, "Token"),
        (TYPE_URL, "URL"),
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
