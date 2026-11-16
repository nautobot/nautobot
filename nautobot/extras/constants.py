# Webhook content types
HTTP_CONTENT_TYPE_JSON = "application/json"

# Explicit Content-Type for Kubernetes API calls that send a JSON body (Job create/delete).
# RFC 9110 section 8.3: a sender SHOULD send Content-Type when it knows the media type.
# kubernetes>=37 omits it on these calls and ignores `_content_type` (kubernetes-client/python#2782).
# urllib3-future, which replaces urllib3 when installed (e.g. via niquests), then defaults str bodies to
# text/plain and the API server returns 415 (jawah/urllib3.future#449).
# Pass a copy via `_headers=dict(KUBERNETES_JSON_HEADERS)`: the client writes into the dict it is given.
KUBERNETES_JSON_HEADERS = {"Content-Type": HTTP_CONTENT_TYPE_JSON}

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
    "console_log_default",
    "dryrun_default",
    "hidden",
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

# Job runtime statistics
JOB_RUNTIME_STATISTICS_SAMPLE_SIZE = 50
JOB_RUNTIME_STATISTICS_MINIMUM_SAMPLES = 3

# ChangeLog Truncation Length
CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL = 400
CHANGELOG_MAX_OBJECT_REPR = 200

# JobResult custom Celery kwargs
JOB_RESULT_CUSTOM_CELERY_KWARGS = (
    "nautobot_job_profile",
    "nautobot_job_queue_type",
    "nautobot_job_console_log",
    "nautobot_job_branch_name",
    "nautobot_job_job_model_id",
    "nautobot_job_scheduled_job_id",
    "nautobot_job_user_id",
    "nautobot_job_ignore_singleton_lock",
)

PENDING_WORKFLOWS_ERROR_CODE = "definition_has_pending_workflows"
