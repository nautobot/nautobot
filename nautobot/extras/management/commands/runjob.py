import time

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.management.utils import report_job_status, validate_job_and_job_data
from nautobot.extras.models import Job, JobResult
from nautobot.extras.utils import get_required_run_param_names


class Command(BaseCommand):
    help = (
        "Enqueue or locally execute a Nautobot job by its class path. "
        "Can run the job on a Celery worker (default) or directly on the local system (--local). "
        "Blocks until the job reaches a terminal state and reports the final status."
    )

    def add_arguments(self, parser):
        parser.add_argument("job", help="Job in the Python module form: `<module_name>.<JobClassName>`")
        parser.add_argument(
            "--profile",
            action="store_true",
            help="Run cProfile on the job execution and write the result to the disk under /tmp.",
        )
        parser.add_argument(
            "-u",
            "--username",
            help="User account to impersonate as the requester of this job",
            required=True,
        )
        parser.add_argument(
            "-l",
            "--local",
            action="store_true",
            help="Run the job on the local system and not on a worker.",
        )
        parser.add_argument("-d", "--data", type=str, help="JSON string that populates the `data` variable of the job.")

    def handle(self, *args, **options):
        """Look up the job and user, then either run locally or enqueue on a worker.

        Expects the job argument in '<module_name>.<JobClassName>' form. Resolves the
        user by username and the job model by class path, then branches:

        - If --local: creates a JobResult directly and delegates execution to the
                      'execute_job_result' management command in the current process,
                      optionally with cProfile (--profile) and input data (--data).
        - Otherwise:  validates the job and input data, then enqueues the job via
                      JobResult.enqueue_job, dispatching it to a Celery worker.

        In both cases, polls until the job reaches a terminal state and reports
        the final status via report_job_status.
        """
        if "." not in options["job"]:
            raise CommandError('Job must be specified in the Python module form: "<module_name>.<JobClassName>"')
        User = get_user_model()
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist as exc:
            raise CommandError("No such user") from exc

        job_class_path = options["job"]
        job_model = Job.objects.get_for_class_path(job_class_path)

        data = validate_job_and_job_data(self, user, job_class_path, options.get("data"))
        if options["local"]:
            required_run_params = get_required_run_param_names(job_model.class_path)
            if required_run_params is not None:
                missing_kwargs = required_run_params - data.keys()
                if missing_kwargs:
                    raise CommandError(f"Missing required job parameters: {missing_kwargs}")
            job_result = JobResult.objects.create(
                name=job_model.name,
                job_model=job_model,
                user=user,
            )
            schedule = data.get("schedule", None)
            celery_kwargs = data.get("celery_kwargs", None)
            task_queue = data.get("task_queue", None)
            ignore_singleton_lock = data.get("ignore_singleton_lock", None)
            job_celery_kwargs = JobResult._build_celery_kwargs(
                job_model=job_model,
                user=user,
                task_queue=task_queue,
                console_log=False,
                profile=options["profile"],
                ignore_singleton_lock=ignore_singleton_lock,
                schedule=schedule,
                celery_kwargs=celery_kwargs,
            )

            job_result.celery_kwargs = job_celery_kwargs
            job_result.save()
            call_command(
                "execute_job_result",
                f"{job_result.pk!s}",
                profile=options["profile"],
                data=options.get("data"),
                stdout=self.stdout,
            )
        else:
            job_result = JobResult.enqueue_job(job_model, user, profile=options["profile"], **data)

        # Wait on the job to finish
        while job_result.status not in JobResultStatusChoices.READY_STATES:
            time.sleep(1)
            job_result.refresh_from_db()

        # Report on success/failure
        report_job_status(self, job_result)
