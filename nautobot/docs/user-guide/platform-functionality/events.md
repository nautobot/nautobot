# Event Notifications

+++ 2.4.0

Nautobot provides and uses an system capable of publishing event notifications on a variety of "topics" (sometimes known as "channels") to a variety of other systems ("brokers", "consumers", or "subscribers"), such as Redis publish/subscribe (Pub/Sub) and similar.

!!! info
    In the future, Nautobot [webhooks](webhook.md) and [job hooks](jobs/jobhook.md) will likely be reimplemented as consumers of the event notification system.

## Subscribing to Event Notifications

Any subclass of the `nautobot.core.events.EventBroker` abstract base class can be instantiated and then registered as a subscriber to event notifications. Typically you will do this in your `nautobot_config.py` or equivalent configuration file:

```py title="nautobot_config.py"
import logging
from nautobot.core.events import register_event_broker, SyslogEventBroker, RedisEventBroker

# Send event notifications to the syslog with a severity of INFO
register_event_broker(SyslogEventBroker(level=logging.INFO))
# Also send event notifications to the identified Redis instance
register_event_broker(RedisEventBroker(url="redis://redis.example.com:6379/0"))
```

At present, the following event broker classes are built in to Nautobot; additional classes can be defined by an App, by a Python package, or even inline in your `nautobot_config.py` as desired.

### Syslog Event Broker

`nautobot.core.events.SyslogEventBroker(log_level=logging.INFO)`

This event broker sends messages to the syslog, using Python logger `nautobot.events.<topic>` and formatting the event payload as a JSON string.

### Redis Event Broker

`nautobot.core.events.RedisEventBroker(url=...)`

This event broker sends messages to Redis Pub/Sub.

## Event Topics

Currently the following topics are documented as published by Nautobot core, but Apps can make use of this system to publish other topics as well.

### Record Change Events

* `nautobot.create.<app>.<model>` (such as `nautobot.create.dcim.device`) - a new record was created
* `nautobot.update.<app>.<model>` (such as `nautobot.update.ipam.ipaddress`) - an existing record was saved
* `nautobot.delete.<app>.<model>` (such as `nautobot.delete.extras.tag`) - an existing record was deleted.

The data payload associated with events of any of the above topics has the following keys:

* `context` - a dictionary providing context about the event, including:
    * `user_name` - The name of the user account associated with the change
    * `timestamp` - The date and time at which the event occurred
    * `request_id` - A UUID that can be used to correlate multiple changes associated with a single request or action.
    * `change_context` - One of `Web`, `Job`, `Job hook`, `ORM`, or `Unknown`, indicating what type of action caused the event
    * `change_context_detail` - A string optionally providing more information about the change context. For example, for a `Web` change context, this might indicate which URL pattern or view was involved in the event.
* `prechange` - a dictionary of record attributes and their values *before* the event occurred (or null, in the case of a `nautobot.create` event)
* `postchange` - a dictionary of record attributes and their values *after* the event occurred (or null, in the case of a `nautobot.delete` event)
* `differences` - a dictionary with keys `added` and `removed`, each of which is a dictionary of record attributes that changed in the event, providing a convenient alternative to manually comparing the prechange and postchange data.

### User Events

* `nautobot.users.user.login` - a user has logged in.
* `nautobot.users.user.logout` - a user has logged out.
* `nautobot.users.user.change_password` - a user has changed their password
* `nautobot.admin.user.change_password` - an admin changed a user password

The data payload associated with events of any of the above topics has the following keys:

* `data` - A dictionary of the affected user record attributes and their value.

    Example payload:

    ```json
        {
            "data": {
                "id": "9747d106-02f2-40e4-bef6-2ffd88c559d6",
                "object_type": "users.user",
                "display": "admin",
                "url": "/api/users/users/9747d106-02f2-40e4-bef6-2ffd88c559d6/",
                "natural_slug": "admin_9747",
                "last_login": "2024-10-22T08:46:08.194925Z",
                "is_superuser": true,
                "username": "admin",
                "first_name": "",
                "last_name": "",
                "email": "a@a.com",
                "is_staff": true,
                "is_active": true,
                "date_joined": "2024-10-22T04:35:28.886682Z",
                "groups": []
            }
        }
    ```

### Job Events

* `nautobot.jobs.job.started` - A job has started.
* `nautobot.jobs.job.completed` - A job has completed (successfully or not).

The data payload associated with events of any of the above topics has the following keys:

* `job_result_id` - The id of the Job Result.
* `job_name` - The name of the job.
* `user_name` - The name of the user account associated with the job.
* `job_kwargs` - The job data (only if job `has_sensitive_variables` attribute is `False`).
* `job_output` - The output of the completed job (only in case of `nautobot.jobs.job.completed`).
* `einfo` - The stacktrace of job failure (only in the case of `nautobot.jobs.job.completed` and null if job competed without a failure).

### Scheduled Job Approval Events

* `nautobot.jobs.approval.approved` - A scheduled job that requires approval has been approved.
* `nautobot.jobs.approval.denied` - A scheduled job that requires approval has been denied.

The data payload associated with events of any of the above topics has the following keys:

* `data` - A dictionary of the scheduled job record attributes and their values.

     Example payload:

     ```json
        {
            "data": {
                "id": "5c09a476-8c15-428c-a94c-41e0ffc76564",
                "object_type": "extras.scheduledjob",
                "display": "test1: immediately",
                "url": "/api/extras/scheduled-jobs/5c09a476-8c15-428c-a94c-41e0ffc76564/",
                "natural_slug": "test1_5c09",
                "queue": "",
                "time_zone": "UTC",
                "name": "test1",
                "task": "dry_run.TestDryRun",
                "interval": "immediately",
                "args": [],
                "kwargs": {},
                "celery_kwargs": {},
                "one_off": false,
                "start_time": "2024-10-28T08:25:32.637433Z",
                "enabled": true,
                "last_run_at": null,
                "total_run_count": 0,
                "date_changed": "2024-10-28T08:25:32.640275Z",
                "description": "",
                "approval_required": true,
                "approved_at": null,
                "crontab": "",
                "job_model": {
                    "id": "d56857d7-d0b5-42e2-8bc5-b93c3cee4da9",
                    "object_type": "extras.job",
                    "display": "TestDryRun",
                    "url": "/api/extras/jobs/d56857d7-d0b5-42e2-8bc5-b93c3cee4da9/",
                    "natural_slug": "dry-run_testdryrun_d568",
                    "task_queues": [
                        "celery Job Queue - 10",
                        "celery Job Queue - 18",
                        "celery Job Queue - 2",
                        "celery Job Queue - 22",
                        "celery Job Queue - 8",
                        "default",
                        "kubernetes Job Queue - 13",
                        "kubernetes Job Queue - 25"
                    ],
                    "task_queues_override": true,
                    "module_name": "dry_run",
                    "job_class_name": "TestDryRun",
                    "grouping": "dry_run",
                    "name": "TestDryRun",
                    "description": "",
                    "installed": true,
                    "enabled": false,
                    "is_job_hook_receiver": false,
                    "is_job_button_receiver": false,
                    "has_sensitive_variables": true,
                    "hidden": false,
                    "dryrun_default": false,
                    "read_only": false,
                    "soft_time_limit": 0.0,
                    "time_limit": 0.0,
                    "supports_dryrun": true,
                    "grouping_override": false,
                    "name_override": false,
                    "description_override": false,
                    "dryrun_default_override": false,
                    "hidden_override": false,
                    "soft_time_limit_override": false,
                    "time_limit_override": false,
                    "has_sensitive_variables_override": false,
                    "job_queues_override": true,
                    "default_job_queue_override": false,
                    "default_job_queue": {
                        "id": "788a60f8-42bb-4a5d-a8f4-4a93916115fd",
                        "object_type": "extras.jobqueue",
                        "url": "/api/extras/job-queues/788a60f8-42bb-4a5d-a8f4-4a93916115fd/"
                    },
                    "created": "2024-10-20T14:07:11.628000Z",
                    "last_updated": "2024-10-20T14:08:07.305000Z",
                    "notes_url": "/api/extras/jobs/d56857d7-d0b5-42e2-8bc5-b93c3cee4da9/notes/",
                    "custom_fields": {}
                },
                "job_queue": null,
                "user": {
                    "id": "4bbdbb24-93b9-4fdd-a9dc-8faed9d1ae50",
                    "object_type": "users.user",
                    "display": "nautobotuser",
                    "url": "/api/users/users/4bbdbb24-93b9-4fdd-a9dc-8faed9d1ae50/",
                    "natural_slug": "nautobotuser_4bbd",
                    "last_login": "2024-10-28T08:25:32.633690Z",
                    "is_superuser": false,
                    "username": "nautobotuser",
                    "first_name": "",
                    "last_name": "",
                    "email": "",
                    "is_staff": false,
                    "is_active": true,
                    "date_joined": "2024-10-28T08:25:32.617444Z",
                    "config_data": {}
                },
                "approved_by_user": null
            }
        }
     ```
