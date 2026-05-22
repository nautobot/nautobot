"""``run_event_consumers`` — long-running management command that drives the event-consumer framework.

For each consumer registered in ``settings.EVENT_CONSUMERS``:

1. Resolves the configured ``SecretsGroup`` → username → Django ``User``. This is the user
   that will own every ``JobResult`` enqueued by this consumer.
2. Resolves each ``JOB_BINDINGS`` entry's ``job_class`` (a dotted-path string stored at
   settings-load time) to the corresponding ``Job`` database row.
3. Spawns a worker thread that calls ``consumer.subscribe(consumer.include_topics)`` and
   iterates ``consumer.read()``. For each ``ConsumedEvent``: applies ``exclude_topics``
   filtering, looks up matching bindings, enqueues each matching Job via
   ``JobResult.enqueue_job(...)``, then acks the source event (or nacks if enqueueing
   raised).

Handles ``SIGTERM`` / ``SIGINT`` cleanly: sets a shared shutdown event, calls
``consumer.close()`` on each consumer, and joins all worker threads with a configurable
timeout.
"""

import logging
import signal
import threading
import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils.module_loading import import_string

from nautobot.core.events import _EVENT_CONSUMERS, is_topic_match
from nautobot.extras.models import Job, JobResult, SecretsGroup

logger = logging.getLogger(__name__)

# How often (seconds) the main thread polls thread liveness in --exit-when-idle mode.
_LIVENESS_POLL_INTERVAL = 0.1


class Command(BaseCommand):
    help = (
        "Read events from all registered EventConsumers and enqueue matching EventConsumerJob "
        "subclasses. Runs until SIGTERM/SIGINT (or until --exit-when-idle is set and every "
        "consumer's read() iterator has exhausted)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--consumer-name",
            default=None,
            help="If supplied, only run the consumer with this configured name. "
            "Useful for debugging or running consumers across separate processes.",
        )
        parser.add_argument(
            "--shutdown-timeout",
            type=float,
            default=30.0,
            help="Seconds to wait for worker threads to finish during graceful shutdown. Default: 30.",
        )
        parser.add_argument(
            "--exit-when-idle",
            action="store_true",
            help="Exit cleanly once every consumer's read() iterator has exhausted. "
            "Intended for tests and one-shot batch processing; for production, leave this off so "
            "the command blocks on SIGTERM/SIGINT.",
        )

    def handle(self, *args, **options):  # pylint: disable=too-many-locals
        consumer_filter = options.get("consumer_name")
        shutdown_timeout = options["shutdown_timeout"]
        exit_when_idle = options["exit_when_idle"]

        entries = list(_EVENT_CONSUMERS)
        if consumer_filter:
            entries = [e for e in entries if e["name"] == consumer_filter]

        if not entries:
            suffix = f" matching --consumer-name={consumer_filter!r}" if consumer_filter else ""
            raise CommandError(f"No EventConsumers are registered{suffix}.")

        # Resolve everything (Users, Jobs) BEFORE spawning threads so we fail fast.
        prepared = []
        for entry in entries:
            user = self._resolve_user(entry)
            job_models_by_path = self._resolve_job_models(entry)
            prepared.append((entry, user, job_models_by_path))
            self.stdout.write(
                self.style.SUCCESS(
                    f"Consumer {entry['name']!r}: resolved user {user.username!r} and "
                    f"{len(job_models_by_path)} job binding(s)."
                )
            )

        shutdown_event = threading.Event()
        consumers = [entry["consumer"] for entry, _, _ in prepared]
        self._install_signal_handlers(shutdown_event, consumers)

        threads = []
        for entry, user, job_models_by_path in prepared:
            thread = threading.Thread(
                target=self._worker_loop,
                args=(entry, user, job_models_by_path, shutdown_event),
                name=f"event-consumer-{entry['name']}",
                daemon=True,
            )
            thread.start()
            threads.append(thread)

        self.stdout.write(
            self.style.SUCCESS(
                f"Started {len(threads)} consumer worker thread(s). Send SIGTERM or SIGINT to shut down."
            )
        )

        try:
            if exit_when_idle:
                while not shutdown_event.is_set() and any(t.is_alive() for t in threads):
                    time.sleep(_LIVENESS_POLL_INTERVAL)
            else:
                shutdown_event.wait()
        finally:
            shutdown_event.set()
            for consumer in consumers:
                try:
                    consumer.close()
                except Exception:  # pylint: disable=broad-except
                    logger.exception("Error closing consumer during shutdown")
            for thread in threads:
                thread.join(timeout=shutdown_timeout)
            still_alive = [t.name for t in threads if t.is_alive()]
            if still_alive:
                logger.warning("Worker thread(s) did not exit within %ss: %s", shutdown_timeout, still_alive)
            self.stdout.write(self.style.SUCCESS("All consumer workers stopped."))

    @staticmethod
    def _resolve_user(entry):
        """Resolve the Django ``User`` that this consumer's enqueued Jobs will run as."""
        secrets_group_name = entry.get("secrets_group_name")
        if not secrets_group_name:
            raise CommandError(
                f"Consumer {entry['name']!r}: no SECRETS_GROUP configured — the framework "
                f"requires a SecretsGroup that supplies the Job-executing username."
            )
        try:
            secrets_group = SecretsGroup.objects.get(name=secrets_group_name)
        except SecretsGroup.DoesNotExist as exc:
            raise CommandError(
                f"Consumer {entry['name']!r}: SecretsGroup {secrets_group_name!r} does not exist."
            ) from exc
        try:
            username = secrets_group.get_secret_value(
                access_type=entry["user_access_type"],
                secret_type=entry["user_secret_type"],
            )
        except Exception as exc:  # SecretsGroupAssociation.DoesNotExist, SecretError, etc.
            raise CommandError(
                f"Consumer {entry['name']!r}: unable to retrieve username from SecretsGroup "
                f"{secrets_group_name!r} (access_type={entry['user_access_type']!r}, "
                f"secret_type={entry['user_secret_type']!r}): {exc}"
            ) from exc
        if not username:
            raise CommandError(
                f"Consumer {entry['name']!r}: SecretsGroup {secrets_group_name!r} returned an empty username."
            )

        user_model = get_user_model()
        try:
            user = user_model.objects.get(username=username, is_active=True)
        except user_model.DoesNotExist as exc:
            raise CommandError(
                f"Consumer {entry['name']!r}: no active user with username={username!r} (sourced from "
                f"SecretsGroup {secrets_group_name!r})."
            ) from exc
        return user

    @staticmethod
    def _resolve_job_models(entry):
        """Resolve every binding's ``job_class_path`` to a ``Job`` model row.

        Resolves up-front so a misconfigured binding fails the whole command at startup
        rather than at first-event time.
        """
        resolved = {}
        for binding in entry["job_bindings"]:
            class_path = binding["job_class_path"]
            if class_path in resolved:
                continue
            module_name, _, class_name = class_path.rpartition(".")
            if not module_name or not class_name:
                raise CommandError(f"Consumer {entry['name']!r}: job_class {class_path!r} is not a valid dotted path.")
            # Touch the import to surface ImportError at startup (also lets pylint see the class).
            try:
                import_string(class_path)
            except ImportError as exc:
                raise CommandError(
                    f"Consumer {entry['name']!r}: cannot import job_class {class_path!r}: {exc}"
                ) from exc
            try:
                resolved[class_path] = Job.objects.get(module_name=module_name, job_class_name=class_name)
            except Job.DoesNotExist as exc:
                raise CommandError(
                    f"Consumer {entry['name']!r}: no Job database row for {class_path!r}. "
                    f"Has 'nautobot-server post_upgrade' been run since the Job was added?"
                ) from exc
        return resolved

    @staticmethod
    def _install_signal_handlers(shutdown_event, consumers):
        def handler(signum, _frame):
            logger.info("run_event_consumers received signal %s; shutting down", signum)
            shutdown_event.set()
            for consumer in consumers:
                try:
                    consumer.close()
                except Exception:  # pylint: disable=broad-except
                    logger.exception("Error closing consumer in signal handler")

        signal.signal(signal.SIGTERM, handler)
        signal.signal(signal.SIGINT, handler)

    @staticmethod
    def _worker_loop(entry, user, job_models_by_path, shutdown_event):
        """Subscribe, read events, dispatch to matching Jobs. Runs in a worker thread."""
        name = entry["name"]
        consumer = entry["consumer"]
        bindings = entry["job_bindings"]
        try:
            consumer.subscribe(consumer.include_topics)
        except Exception:  # pylint: disable=broad-except
            logger.exception("Consumer %s: subscribe failed; worker exiting", name)
            return

        try:
            for event in consumer.read():
                if shutdown_event.is_set():
                    break
                Command._dispatch_event(name, consumer, event, bindings, user, job_models_by_path)
        except Exception:  # pylint: disable=broad-except
            logger.exception("Consumer %s: worker loop crashed", name)

    @staticmethod
    def _dispatch_event(name, consumer, event, bindings, user, job_models_by_path):
        """Filter, enqueue matching Jobs, and ack/nack the consumed event."""
        if consumer.exclude_topics and is_topic_match(event.topic, consumer.exclude_topics):
            consumer.ack(event)
            return

        matched = [b for b in bindings if is_topic_match(event.topic, [b["topic_pattern"]])]
        if not matched:
            logger.warning("Consumer %s: no Job binding matches topic %s; acking", name, event.topic)
            consumer.ack(event)
            return

        try:
            for binding in matched:
                job_model = job_models_by_path[binding["job_class_path"]]
                JobResult.enqueue_job(
                    job_model,
                    user,
                    topic=event.topic,
                    payload=event.payload,
                    headers=event.headers,
                    source_consumer=name,
                    task_queue=binding.get("queue"),
                )
        except Exception:  # pylint: disable=broad-except
            logger.exception("Consumer %s: failed to enqueue Job(s) for topic %s; nacking", name, event.topic)
            consumer.nack(event, requeue=True)
        else:
            consumer.ack(event)
