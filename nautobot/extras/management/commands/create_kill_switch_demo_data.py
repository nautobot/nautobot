"""Management command to generate demo data for the Job Kill Switch feature."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from nautobot.extras.choices import (
    JobResultStatusChoices,
    KillRequestStatusChoices,
    KillTypeChoices,
)
from nautobot.extras.models import Job, JobKillRequest, JobResult

User = get_user_model()


class Command(BaseCommand):
    help = "Generate demo JobResult and JobKillRequest data for the kill switch feature."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all existing JobKillRequest records before creating new ones.",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            count = JobKillRequest.objects.all().delete()[0]
            self.stdout.write(self.style.WARNING(f"Deleted {count} existing JobKillRequest records."))
            # Also clean up demo job results we created previously
            JobResult.objects.filter(name__startswith="[Demo]").delete()

        user = User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR("No users found. Create a user first."))
            return

        # Try to find a real job to reference, but it's optional
        job_model = Job.objects.first()

        now = timezone.now()

        # 1. A running job (killable, no kill request)
        jr_running = JobResult.objects.create(
            name="[Demo] Long Running Sync Job",
            job_model=job_model,
            user=user,
            status=JobResultStatusChoices.STATUS_STARTED,
            date_started=now - timezone.timedelta(hours=2),
            worker="celery@worker-01",
            celery_kwargs={"queue": "default"},
        )
        self.stdout.write(f"  Created running job: {jr_running.pk}")

        # 2. A pending job (killable, no kill request)
        jr_pending = JobResult.objects.create(
            name="[Demo] Queued Config Push",
            job_model=job_model,
            user=user,
            status=JobResultStatusChoices.STATUS_PENDING,
            celery_kwargs={"queue": "default"},
        )
        self.stdout.write(f"  Created pending job: {jr_pending.pk}")

        # 3. A running job with a pending kill request (termination pending)
        jr_terminating = JobResult.objects.create(
            name="[Demo] Stuck Discovery Job",
            job_model=job_model,
            user=user,
            status=JobResultStatusChoices.STATUS_STARTED,
            date_started=now - timezone.timedelta(hours=5),
            worker="celery@worker-02",
            celery_kwargs={"queue": "default"},
        )
        JobKillRequest.objects.create(
            job_result=jr_terminating,
            requested_by=user,
            status=KillRequestStatusChoices.STATUS_PENDING,
        )
        self.stdout.write(f"  Created terminating job (pending kill): {jr_terminating.pk}")

        # 4. A job that was successfully killed by a user
        jr_killed = JobResult.objects.create(
            name="[Demo] Killed Backup Job",
            job_model=job_model,
            user=user,
            status=JobResultStatusChoices.STATUS_REVOKED,
            date_started=now - timezone.timedelta(hours=3),
            date_done=now - timezone.timedelta(hours=1),
            worker="celery@worker-01",
            celery_kwargs={"queue": "default"},
            kill_type=KillTypeChoices.TERMINATE,
            killed_by=user,
            killed_at=now - timezone.timedelta(hours=1),
        )
        JobKillRequest.objects.create(
            job_result=jr_killed,
            requested_by=user,
            status=KillRequestStatusChoices.STATUS_ACKNOWLEDGED,
            acknowledged_at=now - timezone.timedelta(hours=1),
        )
        self.stdout.write(f"  Created killed job (user requested): {jr_killed.pk}")

        # 5. A job that was reaped
        jr_reaped = JobResult.objects.create(
            name="[Demo] Reaped Orphan Job",
            job_model=job_model,
            user=user,
            status=JobResultStatusChoices.STATUS_REVOKED,
            date_started=now - timezone.timedelta(days=1),
            date_done=now - timezone.timedelta(hours=6),
            worker="celery@worker-gone",
            celery_kwargs={"queue": "default"},
            kill_type=KillTypeChoices.REAP,
            killed_by=None,
            killed_at=now - timezone.timedelta(hours=6),
        )
        JobKillRequest.objects.create(
            job_result=jr_reaped,
            requested_by=None,
            status=KillRequestStatusChoices.STATUS_ACKNOWLEDGED,
            acknowledged_at=now - timezone.timedelta(hours=6),
        )
        self.stdout.write(f"  Created reaped job: {jr_reaped.pk}")

        # 6. A kill attempt that failed
        jr_failed_kill = JobResult.objects.create(
            name="[Demo] Unkillable Job",
            job_model=job_model,
            user=user,
            status=JobResultStatusChoices.STATUS_STARTED,
            date_started=now - timezone.timedelta(hours=4),
            worker="celery@worker-03",
            celery_kwargs={"queue": "default"},
        )
        JobKillRequest.objects.create(
            job_result=jr_failed_kill,
            requested_by=user,
            status=KillRequestStatusChoices.STATUS_FAILED,
            acknowledged_at=now - timezone.timedelta(minutes=30),
            error_detail="ConnectionError: Unable to reach Celery broker at redis:6379",
        )
        self.stdout.write(f"  Created failed kill job: {jr_failed_kill.pk}")

        # 7. A normally completed job (no kill fields — baseline comparison)
        JobResult.objects.create(
            name="[Demo] Normal Completed Job",
            job_model=job_model,
            user=user,
            status=JobResultStatusChoices.STATUS_SUCCESS,
            date_started=now - timezone.timedelta(minutes=30),
            date_done=now - timezone.timedelta(minutes=25),
            worker="celery@worker-01",
            celery_kwargs={"queue": "default"},
        )

        self.stdout.write(self.style.SUCCESS("\nCreated 7 demo JobResult records and 4 JobKillRequest records."))
        self.stdout.write("View at: /extras/job-results/ and /extras/job-kill-requests/")
