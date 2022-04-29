# Webhook content types
HTTP_CONTENT_TYPE_JSON = "application/json"

# Registerable extras features
EXTRAS_FEATURES = [
    "config_context_owners",
    "custom_fields",
    "custom_links",
    "custom_validators",
    "dynamic_groups",
    "export_template_owners",
    "export_templates",
    "graphql",
    "job_results",
    "relationships",
    "statuses",
    "webhooks",
]

# Field names that can be inherited from the Job source code or overridden in the Job database model
JOB_OVERRIDABLE_FIELDS = (
    "grouping",
    "name",
    "description",
    "commit_default",
    "hidden",
    "read_only",
    "approval_required",
    "soft_time_limit",
    "time_limit",
)


# Job field length limits
JOB_MAX_NAME_LENGTH = 100  # TODO this should really be a more general-purpose constant, like NAME_MAX_LENGTH
JOB_MAX_SLUG_LENGTH = 320  # 16 source, 100 GitRepository.name, 100 module_name, 100 job_class_name
JOB_MAX_GROUPING_LENGTH = 255
JOB_MAX_SOURCE_LENGTH = 16  # "git", "local", "plugins"


# JobLogEntry Truncation Length
JOB_LOG_MAX_GROUPING_LENGTH = 100
JOB_LOG_MAX_LOG_OBJECT_LENGTH = 200
JOB_LOG_MAX_ABSOLUTE_URL_LENGTH = 255
