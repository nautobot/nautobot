"""Shared helpers for Nautobot core management commands."""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import CommandError

from nautobot.extras.management.utils import validate_job_and_job_data
from nautobot.extras.models import Job, JobResult


def get_user(username):
    """Look up a User by username, raising CommandError if not found."""
    User = get_user_model()
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        raise CommandError(f'No such user "{username}"') from None


def get_content_type(value):
    """Look up a ContentType from an "app_label.model" string, raising CommandError if not found."""
    try:
        app_label, model = value.lower().split(".")
        # Note: a direct .get() (not get_by_natural_key) is deliberate — the latter uses ContentType's
        # process-level cache, which goes stale across test databases and causes FK violations.
        return ContentType.objects.get(app_label=app_label, model=model)
    except (ValueError, ContentType.DoesNotExist):
        raise CommandError(
            f'Invalid content type "{value}"; expected "app_label.model" form, e.g. "dcim.device"'
        ) from None


def run_system_job_locally(command, user, job_class_path, data):
    """
    Run a system Job synchronously in the current process and hand back its JobResult.

    `runjob --local` runs a Job this way too, but reports its status and returns nothing; a command that
    has to do something with what the Job produced -- write out an exported file, say -- needs the
    JobResult itself, which is what this adds.

    `validate_job_and_job_data()` is what makes this equivalent to running the Job from the UI: it
    checks that the Job is installed and enabled, and that `user` has permission to run it. Without it,
    `-u` would be a way to run a Job as a user who is not allowed to.

    Returns:
        (JobResult): The completed job result.
    """
    validate_job_and_job_data(command, user, job_class_path, data)
    job_model = Job.objects.get_for_class_path(job_class_path)
    return JobResult.execute_job(job_model=job_model, user=user, job_kwargs=data)
