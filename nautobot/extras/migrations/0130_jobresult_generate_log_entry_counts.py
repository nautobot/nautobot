"""Migration to populate job_results.*_log_counts on existing JobResults."""

from django.db import migrations
from django.db.models import Count, Q


def _populate_log_counts(apps, *_):
    JobResult = apps.get_model("extras", "JobResult")
    job_results_missing_counts = JobResult.objects.filter(
        Q(debug_log_count=None)
        | Q(success_log_count=None)
        | Q(info_log_count=None)
        | Q(warning_log_count=None)
        | Q(error_log_count=None)
    )
    for job_result in job_results_missing_counts:
        db_log_counts = job_result.job_log_entries.aggregate(
            debug_log_count=Count("pk", filter=Q(log_level="debug")),
            success_log_count=Count("pk", filter=Q(log_level="success")),
            info_log_count=Count("pk", filter=Q(log_level="info")),
            warning_log_count=Count("pk", filter=Q(log_level="warning")),
            error_log_count=Count(
                "pk",
                filter=Q(log_level__in=["failure", "error", "critical"]),
            ),
        )
        job_result.debug_log_count = db_log_counts["debug_log_count"]
        job_result.success_log_count = db_log_counts["success_log_count"]
        job_result.info_log_count = db_log_counts["info_log_count"]
        job_result.warning_log_count = db_log_counts["warning_log_count"]
        job_result.error_log_count = db_log_counts["error_log_count"]
        job_result.save()


class Migration(migrations.Migration):
    dependencies = [
        ("extras", "0129_jobresult_debug_log_count_jobresult_error_log_count_and_more"),
    ]

    operations = [
        migrations.RunPython(code=_populate_log_counts, reverse_code=migrations.RunPython.noop),
    ]
