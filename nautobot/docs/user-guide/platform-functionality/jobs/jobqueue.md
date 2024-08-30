# Job Queues

+++ 2.4.0

JobQueue instances represent the queues that nautobot [jobs](./index.md) can be run on. It is introduced as an alternative to `task_queues` attribute on the Job model to define the eligible queues for this job.

The JobQueue model has `name` and `queue_type` as required attributes. The `name` attribute has to be unique on each Job Queue and there are currently two supported queue types: "celery" and "kubernetes". The user can optionally assign a [tenant](../../core-data-model/tenancy/tenant.md) instance to a Job Queue.

You can access the Job instances that the Job Queue is assigned to through the `jobs` attribute from the Job Queue side.

```python
>>> JobQueue.objects.first()
<JobQueue: celery: celery Job Queue - 2>
>>> job_queue = JobQueue.objects.first()
>>> job_queue.jobs.all()
<JobQuerySet [<Job: Export Object List>, <Job: Git Repository: Dry-Run>, <Job: Git Repository: Sync>, <Job: Import Objects>, <Job: Logs Cleanup>, <Job: Refresh Dynamic Group Caches>]>
```

Conversely, you can access the Job Queues that a Job instance is assigned to through the `job_queues` attribute.

```python
>>> Job.objects.first()
<Job: Custom form.>
>>> job = Job.objects.first()
>>> job.job_queues.all()
<RestrictedQuerySet [<JobQueue: celery: celery Job Queue - 2>, <JobQueue: celery: celery Job Queue - 6>, <JobQueue: celery: default>]>
```

JobQueueAssignment is a concrete through table model that represents the relationships between Jobs and Job Queues. Check out its [documentation](./jobqueueassignment.md) for more details.
