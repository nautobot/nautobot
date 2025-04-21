
## Writing Jobs
<!-- move:getting-started.md -->
### Introduction to Writing Jobs
<!-- move:getting-started.md -->
!!! warning
    Make sure your Job subclasses inherit from `nautobot.apps.jobs.Job` and *not* from `nautobot.extras.models.Job` instead; if you mistakenly inherit from the latter, Django will think you want to define a new database model!

The most basic structure of a Python file providing one or more Jobs is as follows:

```python
from nautobot.apps import jobs

name = "My Group Of Jobs"  # optional, but recommended to define a grouping name

class MyNewJob(jobs.Job):
    class Meta:
        # metadata attributes go here
        name = "My New Job"
        # ... etc.

    # input variable definitions go here
    some_text_input = jobs.StringVar(...)
    # ... etc.

    def run(self, *, some_text_input, ...):
        # code to execute when the Job is run goes here
        self.logger.info("some_text_input: %s", some_text_input)

jobs.register_jobs(MyNewJob)
```

Each Job class will implement some or all of the following components:

* [Module](#module-metadata-attributes) and class [metadata attributes](#class-metadata-attributes), configuring the system-level behavior of the Job and providing for documentation and discoverability by users.
* A set of [variables](#variables) for user input via the Nautobot UI or API.
* The [`run()` method](#the-run-method), which is the only **required** attribute on a Job class and receives the user input values as keyword arguments.
* Optionally, any of the special methods [`before_start()`](#the-before_start-method), [`on_success()`](#the-on_success-method), [`on_failure()`](#the-on_failure-method), and/or [`after_return()`](#the-after_return-method).

It's important to understand that Jobs execute on the server asynchronously as background tasks; they log messages and report their status to the database by updating [`JobResult`](../../user-guide/platform-functionality/jobs/models.md#job-results) records and creating [`JobLogEntry`](../../user-guide/platform-functionality/jobs/models.md#job-log-entry) records.
<!-- move:getting-started.md -->
!!! note "About detection of changes while developing a Job"
    When actively developing a Job utilizing a development environment it's important to understand that the "automatically reload when code changes are detected" debugging functionality provided by `nautobot-server runserver` does **not** automatically restart the Celery `worker` process when code changes are made; therefore, it is required to restart the `worker` after each update to your Job source code or else it will continue to run the version of the Job code that was present when it first started. In the Nautobot core development environment, we use `watchmedo auto-restart` as a helper tool to auto-restart the workers as well on code changes; you may wish to configure your local development environment similarly for convenience.

    Additionally, as of Nautobot 1.3, the Job database records corresponding to installed Jobs are *not* automatically refreshed when the development server auto-restarts. If you make changes to any of the class and module metadata attributes described in the following sections, the database will be refreshed to reflect these changes only after running `nautobot-server migrate` or `nautobot-server post_upgrade` (recommended) or if you manually edit a Job database record to force it to be refreshed. The exception here is Git-repository-provided Jobs; resyncing the Git repository through Nautobot will also trigger a refresh of the Job records corresponding to this repository's contents.

### Job Registration
<!-- move:getting-started.md -->
+/- 2.0.0 "`register_jobs()` is now required"

All Job classes, including `JobHookReceiver` and `JobButtonReceiver` classes must be registered at **import time** using the `nautobot.apps.jobs.register_jobs` method. This method accepts one or more Job classes as arguments. You must account for how your Jobs are imported when deciding where to call this method.

#### Registering Jobs in `JOBS_ROOT` or Git Repositories

Only top level module names within `JOBS_ROOT` are imported by Nautobot at runtime. This means that if you're using submodules, you need to ensure that your Jobs are either registered in your top level `__init__.py` or that this file imports your submodules where the Jobs are registered:

```py title="$JOBS_ROOT/my_jobs/__init__.py"
from . import my_job_module
```

```py title="$JOBS_ROOT/my_jobs/my_job_module.py"
from nautobot.apps.jobs import Job, register_jobs

class MyJob(Job):
    ...

register_jobs(MyJob)
```

Similarly, only the `jobs` module is loaded from Git repositories. If you're using submodules, you need to ensure that your Jobs are either registered in the repository's `jobs/__init__.py` or that this file imports your submodules where the Jobs are registered.

If not using submodules, you should register your Job in the file where it is defined.

Examples of the different directory structures when registering Jobs in Git repositories:

!!! note "`__init__.py`"
    Take note of the `__init__.py` at the root of the repository.  This is required to register Jobs in a Git repository.

``` title="jobs.py"
.
├── __init__.py
└── jobs.py
```

``` title="submodule"
.
├── __init__.py
└── jobs
    ├── __init__.py
    └── my_job_module.py
```

#### Registering Jobs in an App

Apps should register Jobs in the module defined in their [`NautobotAppConfig.jobs`](../apps/api/nautobot-app-config.md#nautobotappconfig-code-location-attributes) property. This defaults to the `jobs` module of the App.
