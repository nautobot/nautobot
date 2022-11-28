# Celery Task Queues

If you're planning to run multiple jobs, leverage job hooks or are finding that your jobs are taking too long to complete you may want to consider deploying multiple celery workers with different queues for different types of tasks.

## How Celery Task Queues Work

The default celery behavior is:

- [`--queue celery`](https://docs.celeryq.dev/en/stable/reference/cli.html#cmdoption-celery-worker-Q)
- [`--concurrency`](https://docs.celeryq.dev/en/stable/reference/cli.html#cmdoption-celery-worker-c) set to the number of CPUs detected on the system
- [`worker_prefetch_multiplier=4`](https://docs.celeryq.dev/en/stable/userguide/configuration.html#std-setting-worker_prefetch_multiplier)

This means that a worker running on a 4 core system will run 4 tasks concurrently and reserve a maximum of 16 more tasks from the queue named `celery`. If you have a mixture of long running and short running tasks with a single queue, you could find your long running tasks blocking the shorter tasks.

## Recommended Worker Deployment

Each environment is unique but it's generally a good idea to add at least one extra worker on a separate queue for running jobs. Nautobot uses the default `celery` queue to perform some background tasks and if the queue is full of long running jobs these system tasks could take a long time to execute. This could cause performance problems or unexpected behavior in Nautobot. A new worker can be deployed on a separate queue by using the [`nautobot-worker.service` systemd service](../installation/services.md#celery-worker) and modifying the `ExecStart` line to include a [`--queues` option](https://docs.celeryq.dev/en/stable/reference/cli.html#cmdoption-celery-worker-Q). Example:

```ini
ExecStart=/opt/nautobot/bin/nautobot-server celery worker --loglevel INFO --pidfile /var/tmp/nautobot-worker-jobqueue.pid --queues job_queue
```

This will create a worker that will only process tasks sent to the `job_queue` celery queue. You can use this worker to run jobs while the rest of Nautobot's background tasks will be processed by the default celery worker listening to the `celery` queue.

!!! info
    Workers can be configured to listen to multiple queues by supplying a comma separated list of queues to the `--queues` argument. See the [celery workers guide](https://docs.celeryq.dev/en/stable/userguide/workers.html#queues) for more information.

!!! warning
    If a job is sent to a queue that no workers are listening to, that job will remain in pending status until it's purged or a worker starts listening to that queue and processes the job. Be sure that the queue name on the worker and jobs match.

## Concurrency Setting

If you have long running jobs that use little CPU resources you may want to increase your [`--concurrency`](https://docs.celeryq.dev/en/stable/reference/cli.html#cmdoption-celery-worker-c) setting on your worker to increase the number of jobs that run in parallel. For example, you may have a job that logs into a device over ssh and collects some information from the command line. This task could take a long time to run but consume minimal CPU so your system may be able to run many more of these tasks in parallel than the default concurrency setting allows. The `--concurrency` setting can be modified by adding the command line option in the `ExecStart` line in your systemd service:

```ini
ExecStart=/opt/nautobot/bin/nautobot-server celery worker --loglevel INFO --pidfile /var/tmp/nautobot-worker-jobqueue.pid --queues job_queue --concurrency 64
```

You may have to change this setting multiple times to find what works best in your environment.

!!! warning
    Modifying your concurrency setting may increase the CPU and memory load on your celery worker. Only change this setting if you have monitoring systems in place to monitor the system resources on your worker.
