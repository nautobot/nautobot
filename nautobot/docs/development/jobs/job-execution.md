# Programmatic Job Execution

Most users run Jobs through the Nautobot UI or REST API, but there are situations where user need to trigger a Job from Python directly. Nautobot exposes two entry points for this:

| Method | When to use |
|---|---|
| `JobResult.enqueue_job()` | The primary entry point. Run a Job asynchronously (Celery), synchronously (in-process), or via a Kubernetes pod. |
| `JobResult.execute_job()` | Convenience wrapper around `enqueue_job(synchronous=True)`. |

For testing, use [`run_job_for_testing()`](testing.md) instead — it's a thin wrapper around `execute_job()` that handles Job enablement and user setup for you.

+++ 3.2.0

`job_kwargs` is a **required** parameter on `enqueue_job()`, `execute_job()`, and `run_job_for_testing()`. Previously optional, this argument is now mandatory to ensure consistent Job configuration and avoid implicit defaults.

For Jobs that take no input variables, pass `job_kwargs={}` explicitly:

```python
    job_result = JobResult.enqueue_job(job_model=my_job, user=request.user, job_kwargs={})
```

A backward-compatibility layer accepts the old calling style (passing Job parameters as loose `**extra_kwargs`) but logs a warning. If neither `job_kwargs` nor any `**extra_kwargs` are provided, a `ValueError` is raised. This deprecated fallback will be removed in a future release.

## `JobResult.enqueue_job()`

`JobResult.enqueue_job()` is the canonical entry point for running a Job. It creates (or reuses) a `JobResult` record and dispatches the Job to a Celery worker, a Kubernetes pod, or the current process depending on the queue configuration and the `synchronous` flag.

```python
from nautobot.extras.models import Job, JobResult

job_model = Job.objects.get_for_class_path("pass_job.TestPassJob")
job_result = JobResult.enqueue_job(
    job_model=job_model,
    user=request.user,
    job_kwargs={"device_id": 42},
)
```

### Parameters

| Parameter | Type | Description |
|---|---|---|
| `job_model` | `Job` | The Job to be enqueued for execution. Required. |
| `user` | `User` | User to link to the resulting `JobResult`. Required. |
| `job_kwargs` | `dict` | Keyword arguments forwarded to the Job's `run()` method. **Required** — pass `{}` if the Job takes no parameters. |
| `celery_kwargs` | `dict` | Keyword arguments forwarded to Celery's `apply_async()` / `apply()`. Useful for setting `queue`, priority, and other Celery options. Defaults to `None`. |
| `profile` | `bool` | If `True`, dump cProfile stats on Job execution. Defaults to `False`. |
| `console_log` | `bool` | Enable console logging during execution. Defaults to `False`. |
| `schedule` | `ScheduledJob` | Optional `ScheduledJob` instance to associate with the result. Cannot be combined with `synchronous=True`. |
| `job_queue` | `JobQueue` | Override the queue the Job is sent to. Defaults to the Job's configured default queue. |
| `task_queue` | `str` | Celery queue name. **Deprecated — prefer `job_queue` instead.** Mutually exclusive with `job_queue` when both are set to different values. |
| `job_result` | `JobResult` | Optional existing `JobResult` (status `PENDING`) to modify and reuse. Used by the Kubernetes execution path. The `user` and `job_model` must match. |
| `synchronous` | `bool` | If `True`, run the Job in the current process and block until completion. Defaults to `False`. |
| `ignore_singleton_lock` | `bool` | If `True`, invalidate any existing singleton lock before running. Useful for recovering from a previous run that didn't clean up its lock. Defaults to `False`. |

### Synchronous vs asynchronous

By default (`synchronous=False`), `enqueue_job()` returns immediately after dispatching the task. The returned `JobResult` will be in a `PENDING` state until the worker picks it up. Internally the dispatch happens via `transaction.on_commit()`, so the task is only enqueued once any surrounding database transaction commits successfully — this prevents workers from picking up Jobs that reference data that hasn't been saved yet.

When `synchronous=True`, the Job runs in the current process via `run_job.apply()`. Stdout and stderr are redirected through Celery's logging proxy, and a `SIGALRM`-based soft time limit is enforced based on the Job's configured `soft_time_limit`.

`schedule` and `synchronous=True` are mutually exclusive — scheduled Jobs must always be queued, not run inline.

### Queue resolution

Queue resolution follows this priority:

1. If both `job_queue` and `task_queue` are provided, they must agree on the queue name.
2. If only one is provided, the other is derived from it.
3. If neither is provided, but `celery_kwargs["queue"]` is set, that queue name is used.
4. Otherwise, the Job's `default_job_queue` is used.

If the resolved queue is a Kubernetes queue and `synchronous=False`, `enqueue_job()` delegates to `run_kubernetes_job_and_return_job_result()` to spin up a pod. The pod itself re-enters `enqueue_job()` with `synchronous=True`, which short-circuits past the K8s branch and runs the Job locally inside the pod.

## `JobResult.execute_job()`

`execute_job()` is a thin convenience wrapper that calls `enqueue_job()` with `synchronous=True`.

```python
job_result = JobResult.execute_job(
    job_model=job_model,
    user=request.user,
    job_kwargs={},
)
```

It accepts the same arguments as `enqueue_job()` and forwards them through. Practically it's only used by `run_job_for_testing()`.
