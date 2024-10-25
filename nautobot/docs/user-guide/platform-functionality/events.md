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
