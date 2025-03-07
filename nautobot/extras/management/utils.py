import json

from django.core.management.base import CommandError
from django.utils import timezone

from nautobot.extras.choices import JobResultStatusChoices, LogLevelChoices
from nautobot.extras.jobs import get_job
from nautobot.extras.models import Job, JobLogEntry


def validate_job_and_job_data(command, user, job_class_path, data=None):
    job_data = {}
    try:
        if data:
            job_data = json.loads(data)
    except json.decoder.JSONDecodeError as error:
        raise CommandError(f"Invalid JSON data:\n{error!s}") from error

    if not get_job(job_class_path, reload=True):
        raise CommandError(f'Job "{job_class_path}" not found')

    try:
        job_model = Job.objects.get_for_class_path(job_class_path)
    except Job.DoesNotExist as error:
        raise CommandError(f"Job {job_class_path} does not exist.") from error

    try:
        job_model = Job.objects.restrict(user, "run").get_for_class_path(job_class_path)
    except Job.DoesNotExist:
        raise CommandError(f"User {user.username} does not have permission to run this Job") from None

    if not job_model.installed or job_model.job_class is None:
        raise CommandError("Job is not presently installed")
    if not job_model.enabled:
        raise CommandError("Job is not presently enabled to be run")

    # Run the job and create a new JobResult
    command.stdout.write(f"[{timezone.now():%H:%M:%S}] Running {job_class_path}...")
    return job_data


def report_job_status(command, job_result):
    # Report on success/failure
    job_class_path = job_result.job_model.class_path
    groups = set(JobLogEntry.objects.filter(job_result=job_result).values_list("grouping", flat=True))
    for group in sorted(groups):
        logs = JobLogEntry.objects.filter(job_result__pk=job_result.pk, grouping=group)
        debug_count = logs.filter(log_level=LogLevelChoices.LOG_DEBUG).count()
        info_count = logs.filter(log_level=LogLevelChoices.LOG_INFO).count()
        success_count = logs.filter(log_level=LogLevelChoices.LOG_SUCCESS).count()
        warning_count = logs.filter(log_level=LogLevelChoices.LOG_WARNING).count()
        failure_count = logs.filter(log_level=LogLevelChoices.LOG_FAILURE).count()
        error_count = logs.filter(log_level=LogLevelChoices.LOG_ERROR).count()
        critical_count = logs.filter(log_level=LogLevelChoices.LOG_CRITICAL).count()

        command.stdout.write(
            f"\t{group}: "
            f"{debug_count} debug, "
            f"{info_count} info, "
            f"{success_count} success, "
            f"{warning_count} warning, "
            f"{failure_count} failure, "
            f"{error_count} error, "
            f"{critical_count} critical"
        )

        for log_entry in logs:
            status = log_entry.log_level
            if status == "success":
                status = command.style.SUCCESS(status)
            elif status == "info":
                status = status
            elif status == "warning":
                status = command.style.WARNING(status)
            elif status in ["failure", "error", "critical"]:
                status = command.style.NOTICE(status)

            if log_entry.log_object:
                command.stdout.write(f"\t\t{status}: {log_entry.log_object}: {log_entry.message}")
            else:
                command.stdout.write(f"\t\t{status}: {log_entry.message}")

    if job_result.result:
        command.stdout.write(str(job_result.result))
    if job_result.traceback:
        command.stdout.write(command.style.ERROR(job_result.traceback))

    if job_result.status == JobResultStatusChoices.STATUS_FAILURE:
        status = command.style.ERROR("FAILURE")
    elif job_result.status == JobResultStatusChoices.STATUS_SUCCESS:
        status = command.style.SUCCESS("SUCCESS")
    else:
        status = command.style.WARNING(job_result.status)
    command.stdout.write(f"[{timezone.now():%H:%M:%S}] {job_class_path}: {status}")

    # Wrap things up
    command.stdout.write(f"[{timezone.now():%H:%M:%S}] {job_class_path}: Duration {job_result.duration}")
    command.stdout.write(f"[{timezone.now():%H:%M:%S}] Finished")
