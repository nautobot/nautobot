# Including Jobs

Apps can provide [Jobs](../../../../user-guide/platform-functionality/jobs/index.md) to take advantage of all the built-in functionality provided by that feature (user input forms, background execution, results logging and reporting, etc.).

By default, for each app, Nautobot looks for an iterable named `jobs` within a `jobs.py` file. (This can be overridden by setting `jobs` to a custom value on the app's `NautobotAppConfig`.) A brief example is below; for more details on Job design and implementation, refer to the Jobs feature documentation.

```python
# jobs.py
from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job


class CreateDevices(Job):
    ...


class DeviceConnectionsReport(Job):
    ...


class DeviceIPsReport(Job):
    ...


jobs = [CreateDevices, DeviceConnectionsReport, DeviceIPsReport]
register_jobs(*jobs)
```

+/- 2.0.0
    Because Jobs are now proper Celery tasks, you now must call `register_jobs()` from within your `jobs.py` file when it is imported; any jobs not included in this call will not be available for Celery to schedule and execute.
