# Including Jobs

Apps can provide [Jobs](../../../../user-guide/platform-functionality/jobs/index.md) to take advantage of all the built-in functionality provided by that feature (user input forms, background execution, results logging and reporting, etc.).

By default, for each app, Nautobot looks for an iterable named `jobs` within a `jobs.py` file. (This can be overridden by setting `jobs` to a custom value on the app's `NautobotAppConfig`.) A brief example is below; for more details on Job design and implementation, refer to the Jobs feature documentation.

```python
# jobs.py
from nautobot.extras.jobs import Job


class CreateDevices(Job):
    ...


class DeviceConnectionsReport(Job):
    ...


class DeviceIPsReport(Job):
    ...
```
