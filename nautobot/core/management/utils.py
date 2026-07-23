"""Shared helpers for Nautobot core management commands."""

import json

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
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
    Create a JobResult for the given job and execute it synchronously in the current process.

    This mirrors the `runjob --local` execution path (JobResult creation + the `execute_job_result`
    management command), so behavior is identical to running the job from the UI or a worker.

    Returns:
        (JobResult): The completed (refreshed) job result.
    """
    data_json = json.dumps(data)
    validate_job_and_job_data(command, user, job_class_path, data_json)
    job_model = Job.objects.get_for_class_path(job_class_path)
    job_result = JobResult.objects.create(name=job_model.name, job_model=job_model, user=user)
    job_result.celery_kwargs = JobResult._build_celery_kwargs(
        job_model=job_model,
        user=user,
        task_queue=None,
        console_log=False,
        profile=False,
    )
    job_result.save()
    call_command("execute_job_result", str(job_result.pk), data=data_json, stdout=command.stdout)
    job_result.refresh_from_db()
    return job_result
