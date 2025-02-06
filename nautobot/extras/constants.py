# Webhook content types
HTTP_CONTENT_TYPE_JSON = "application/json"

# Registerable extras features
EXTRAS_FEATURES = [
    "cable_terminations",
    "config_context_owners",
    "custom_fields",  # Deprecated - see nautobot.extras.utils.populate_model_features_registry
    "custom_links",
    "custom_validators",
    "dynamic_groups",
    "export_template_owners",
    "export_templates",
    "graphql_query_owners",
    "graphql",
    "job_results",  # No longer used
    "locations",
    "relationships",  # Deprecated - see nautobot.extras.utils.populate_model_features_registry
    "statuses",
    "webhooks",
]

# Field names that can be inherited from the Job source code or overridden in the Job database model
JOB_OVERRIDABLE_FIELDS = (
    "grouping",
    "name",
    "description",
    "dryrun_default",
    "hidden",
    "approval_required",
    "soft_time_limit",
    "time_limit",
    "has_sensitive_variables",
    "is_singleton",
)


# Job field length limits
JOB_MAX_NAME_LENGTH = 100  # TODO(Glenn): this should really be a more general-purpose constant, like NAME_MAX_LENGTH


# JobLogEntry Truncation Length
JOB_LOG_MAX_GROUPING_LENGTH = 100
JOB_LOG_MAX_LOG_OBJECT_LENGTH = 200
JOB_LOG_MAX_ABSOLUTE_URL_LENGTH = 255

# ChangeLog Truncation Length
CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL = 400
CHANGELOG_MAX_OBJECT_REPR = 200

# JobResult custom Celery kwargs
JOB_RESULT_CUSTOM_CELERY_KWARGS = (
    "nautobot_job_profile",
    "nautobot_job_job_model_id",
    "nautobot_job_scheduled_job_id",
    "nautobot_job_user_id",
    "nautobot_job_ignore_singleton_lock",
)
