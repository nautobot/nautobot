# Job Logging

Nautobot Jobs support rich, structured logging using `self.logger`, with logs surfaced in both the UI and API. This guide covers logging best practices, structured metadata, and important version notes.

## Logging Patterns

+/- 2.0.0

Nautobot logs messages from Jobs in a structured way, storing them as part of the `JobResult` and displaying them in the UI. This enables Jobs to provide real-time feedback, track their progress, and surface success or failure messages clearly to the user.

Use the `self.logger` property to write log messages from within your Job code. These logs appear in the UI and are also saved as [`JobLogEntry`](../../user-guide/platform-functionality/jobs/models.md#job-log-entry) records associated with the current [`JobResult`](../../user-guide/platform-functionality/jobs/models.md#job-results).

## Logging Levels

Nautobot supports standard logging levels, with additional custom levels for success and failure messages:

| Level   | Method                 | Description                               |
|---------|------------------------|-------------------------------------------|
| DEBUG   | `self.logger.debug()`  | Detailed diagnostic information.          |
| INFO    | `self.logger.info()`   | General operational messages.             |
| SUCCESS | `self.logger.success()`| Indicates successful operations.          |
| WARNING | `self.logger.warning()`| Signals potential issues.                 |
| FAILURE | `self.logger.failure()`| Denotes failed operations.                |
| ERROR   | `self.logger.error()`  | Serious errors that prevent execution.    |
| CRITICAL| `self.logger.critical()`| Critical conditions.                      |

!!! note
    `logger.success()` and `logger.failure()` were introduced in versions 2.4.0 and 2.4.5, respectively.

## Configuring Log Levels

You can configure the minimum log level by using `self.logger.setLevel(LOG_LEVEL)` where `LOG_LEVEL` is a string representing the desired value (e.g., "DEBUG", "INFO", "WARNING", etc.). Unfortunately, since loggers in Nautobot share the same configuration, changing the log level for one Job will affect all other Jobs that use the same logger instance.

Instead, the pattern in the following example allows you to control the verbosity of logs only for that specific Job, taking into account the (optional) `debug` parameter passed to it. After setting the log level, only messages at that level or higher will be logged for the Job. Finally, once the Job completes, the log level should be reset to the original level for any subsequent Jobs that use the same logger instance.

<!-- pyml disable-num-lines 10 proper-names -->
!!! example
    ```py
    from nautobot.apps.jobs import BooleanVar, Job

    class MyJob(Job):
        """Example Job demonstrating log level configuration."""

        debug = BooleanVar(default=False, description="Whether to print debug messages")

        def before_start(self, task_id, args, kwargs):
            """Set the logging level before Job starts, based on the debug parameter."""
            super().before_start(task_id, args, kwargs)
            if kwargs.get("debug"):
                self._original_log_level = self.logger.level
                self.logger.setLevel("DEBUG")

        def run(self, **args, **kwargs):
            """Only messages at the configured log level or higher will be logged."""
                self.logger.info("This is an info message.")
                self.logger.debug("This is a debug message.")
                ...

        def after_return(self, status, retval, task_id, args, kwargs, einfo):
            """Return the logger to the default log level after the Job finishes."""
            if kwargs.get("debug"):
                self.logger.setLevel(self._original_log_level)
            return super().after_return(status, retval, task_id, args, kwargs, einfo)
    ```

## Writing Log Messages

<!-- pyml disable-num-lines 10 proper-names -->
!!! example
    ```py
    self.logger.info("Job is starting.")
    self.logger.error("An unexpected error occurred.")
    self.logger.success("Provisioning complete.")
    ```

For most use cases, you'll use `self.logger`. You can also obtain the same logger via `nautobot.extras.jobs.get_task_logger(__name__)`, though this is less common.

## Structured Log Context with `extra`

You can attach structured metadata to log messages using the `extra` parameter. This enables grouping and improves how logs are displayed or queried:

- `grouping`: A logical label used to associate related log messages. It is useful for filtering, context, and organizing output in the API or database
- `object`: A Nautobot object instance to associate with this log message (e.g., a Device)
- `skip_db_logging`: Set to `True` to avoid saving the log message in the database (it will still be visible in the Celery worker log output)

<!-- pyml disable-num-lines 10 proper-names -->
!!! example
    ```py
    self.logger.info(
        "Validated device",
        extra={
            "grouping": "inventory-check",
            "object": device
        }
    )
    ```

To skip writing a log entry to the database but still print it to the console of the Celery worker:

<!-- pyml disable-num-lines 10 proper-names -->
!!! example
    ```py
    self.logger.info("Debugging message", extra={"skip_db_logging": True})
    ```

If `grouping` is not specified, Nautobot uses the current function name as a default. If `object` is omitted, the log is not associated with any model instance.

<!-- pyml disable-num-lines 10 proper-names -->
!!! example
    ```py
    from nautobot.apps.jobs import Job

    class MyJob(Job):
        def run(self):
            self.logger.info("This job is running!", extra={"grouping": "myjobisrunning", "object": self.job_result})
    ```

## Log Message Formatting

Log messages can include Markdown formatting, and [a limited subset of HTML](../../user-guide/platform-functionality/template-filters.md#render_markdown) is also supported for added emphasis in the UI.

## Sanitizing Log Messages

As a security precaution, Nautobot passes all log messages through `nautobot.core.utils.logging.sanitize()` to remove sensitive information like passwords or tokens. You should still avoid logging such values yourself, as this redaction is best-effort. The sanitization behavior can be customized using [`settings.SANITIZER_PATTERNS`](../../user-guide/administration/configuration/settings.md#sanitizer_patterns).

+/- 2.0.0 "Significant API changes"
    The Job class logging functions (example: `self.log(message)`, `self.log_success(obj=None, message=message)`, etc) have been removed. Also, the convenience method to mark a Job as failed, `log_failure()`, has been removed. To replace the functionality of this method, you can log an error message with `self.logger.error()` and then raise an exception to fail the Job. Note that it is no longer possible to manually set the Job Result status as failed without raising an exception in the Job.

+/- 2.0.0
    The `AbortTransaction` class was moved from the `nautobot.utilities.exceptions` module to `nautobot.core.exceptions`. Jobs should generally import it from `nautobot.apps.exceptions` if needed.

+++ 2.4.0 "`logger.success()` added"
    You can now use `self.logger.success()` to log a message at the level `SUCCESS`, which is located between the standard `INFO` and `WARNING` log levels.

+++ 2.4.5 "`logger.failure()` added"
    You can now use `self.logger.failure()` to log a message at the level `FAILURE`, which is located between the standard `WARNING` and `ERROR` log levels.

## Console Logging

+++ 3.1.0

The console_log_default flag controls how job stdout/stderr is handled and where the job is executed.

*If not explicitly provided, `console_log_default` defaults to False.*

### Asynchronous execution (synchronous=False)

```mermaid
flowchart LR
    start[JobResult.enqueue_job]

    subgraph CeleryWorker [Celery Worker]
        direction TB
        direct_call[run_job task
        calls my_app.jobs.my_job directly]

        subgraph console_log_task [run_console_log_job_and_return_job_result]
            executor_celery[JobConsoleLogExecutor
            Celery Task]
        end
    end

    subgraph K8sCluster [Kubernetes Cluster]
        direction TB
        subgraph k8s_pod [K8s Job/Pod - runjob_with_job_result]
            direction TB
            k8s_check{console_log?}
            executor_k8s[JobConsoleLogExecutor]
        end
    end

    subgraph Subprocess [Local Subprocess]
        execute_job_result['nautobot-server execute_job_result'
        runs job via run_job.apply]
    end

    start -- "Default (Enqueue Celery Task)" --> direct_call
    start -- "console_log=True (Enqueue Celery Task)" --> console_log_task
    start -- "K8s Queue (K8s API directly)" --> k8s_pod

    k8s_check -- "True" --> executor_k8s
    k8s_check -- "False" --> execute_job_result

    executor_celery -- "subprocess.Popen" --> execute_job_result
    executor_k8s -- "subprocess.Popen" --> execute_job_result
```

When `console_log=True` and the job is executed asynchronously:

- The `JobResult.celery_kwargs` field is populated and `nautobot_job_console_log` is set.

#### Celery Queue

- A dedicated Celery task `run_console_log_job_and_return_job_result` is queued instead of the standard `run_job` task.
- That task instantiates `JobConsoleLogExecutor` which:
    - Starts a subprocess using:

    ```no-highlight
        nautobot-server execute_job_result <job_result_id>
    ```

    - Reads stdout and stderr line by line from the subprocess.
    - Streams output into the `JobConsoleEntry` table in real time.
    - This allows the UI to display live job output as the job runs.

#### Kubernetes Queue

- A Kubernetes Job/Pod is created via the K8s API running:

    ```no-highlight
        nautobot-server runjob_with_job_result <job_result_id>
    ```

- Inside the pod, `runjob_with_job_result` checks `nautobot_job_console_log` in the `JobResult.celery_kwargs`:
    - **`console_log=True`** — instantiates `JobConsoleLogExecutor` which starts a subprocess:

    ```no-highlight
            nautobot-server execute_job_result <job_result_id>
    ```

    and streams stdout/stderr into the `JobConsoleEntry` table in real time.
    - **`console_log=False`** — calls `JobResult.execute_job()` directly without console log capturing.

### Exporting Console Logs

**Export Console Logs** button is available on the *Console Log* tab of the Job Result detail view.

Clicking the button downloads a plain-text file containing all `JobConsoleEntry` records associated with that Job Result, sorted chronologically. Each line follows the format:

```no-highlight
[HH:MM:SS.mmm] <message>
```

For example:

```no-highlight
[10:23:41.004] Starting job execution
[10:23:41.512] Connected to device 192.0.2.1
[10:23:44.210] Job completed successfully
```

The downloaded file is named `nautobot_job_console_entries_<job_result_pk>.txt`.

!!! note
    The **Export Console Logs** button requires the `extras.view_jobconsoleentry` permission.

### Use cases

1. For debugging
