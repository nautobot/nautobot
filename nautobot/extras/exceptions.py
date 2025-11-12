from django.core.exceptions import ValidationError


class ApprovalRequiredScheduledJobsError(ValidationError):
    """Raised when scheduled jobs requiring approval are found during migration."""
