# Installing Jobs

Nautobot supports three ways to install Jobs:

- **Manually**, by placing Python files under the [`JOBS_ROOT`](../../user-guide/administration/configuration/settings.md#jobs_root) path (defaults to `$NAUTOBOT_ROOT/jobs/`)
- **From a Git repository**, by linking an external repository that contains Jobs
- **As part of an App**, by defining Jobs inside the App's Python module

Each approach supports modular organization, multiple Job classes, and reuse of shared logic. The key difference is how Nautobot loads the files into its job registry and associates them with database Job records.

!!! tip
    Looking to run Jobs in Kubernetes? See [Kubernetes Job Support](../../user-guide/platform-functionality/jobs/kubernetes-job-support.md).

## Manual Installation via `JOBS_ROOT`

Nautobot automatically loads all Python modules found in the `JOBS_ROOT` directory and its subdirectories. Jobs defined here are ideal for quick prototypes or standalone deployments.

!!! note "Refreshing Job records"
    After you add or edit files, restart the Celery worker **and** run `nautobot-server post_upgrade` so Nautobot refreshes its Job database records.

Key requirements:

- Files must contain valid Job classes (subclasses of `nautobot.apps.jobs.Job`)
- Each Job must be registered using `register_jobs()`
- Python files in JOBS_ROOT are imported at application startup. In Celery mode, this includes Celery workers; in Kubernetes mode, only the main web pod imports them.
- To update Job records after editing, **run** `nautobot-server post_upgrade`
- **Jobs are not enabled by default**. You must enable them manually in the UI before they can be run.

Once registered and enabled, Jobs will appear in the **Jobs** tab grouped by the module's `name` attribute.

Example layout:

```text
$NAUTOBOT_ROOT/jobs/
├── __init__.py
├── device_jobs.py
└── inventory/
    ├── __init__.py
    └── check_inventory.py
```

In `device_jobs.py`:

```python
from nautobot.apps.jobs import Job, register_jobs

class CleanupDevices(Job):
    class Meta:
        name = "Cleanup Obsolete Devices"

    def run(self):
        self.logger.info("Cleaning old device entries")

register_jobs(CleanupDevices)
```

## Installation from a Git Repository

To install Jobs from a Git source, link a Git repository to Nautobot via the UI or REST API. ([See Git integration docs](../../user-guide/platform-functionality/gitrepository.md#jobs))

Git repositories are loaded into the module namespace of the `GitRepository.slug` value at startup. For example, if your `slug` value is `my_git_jobs` your Jobs will be loaded into Python as `my_git_jobs.jobs.MyJobClass`.

Key requirements:

- The repo **must** contain a top-level `__init__.py` file
- A `jobs.py` file **or** a `jobs/` subdirectory with a `jobs/__init__.py` file must exist in the repo
- Only the `jobs` module (not the whole repo) is imported
- Each Job must be explicitly registered via `register_jobs()`
- **Jobs are not enabled by default** and must be enabled manually

Once registered and enabled, Jobs will appear in the **Jobs** tab grouped by their module's metadata.

Example layout:

```text
my_repo/
├── __init__.py
└── jobs/
    ├── __init__.py
    └── sync_devices.py
```

In `sync_devices.py`:

```python
from nautobot.apps.jobs import Job, register_jobs

class SyncDevices(Job):
    class Meta:
        name = "Sync Devices from CMDB"

    def run(self):
        self.logger.info("Running external sync...")

register_jobs(SyncDevices)
```

When the repo is synced, Nautobot loads the job class under the path:  
`<slug>.jobs.SyncDevices`, for example, `my_repo.jobs.SyncDevices`.

!!! note "Importing Job Submodules"
    If your `jobs/` module imports submodules, make sure `__init__.py` imports them explicitly.

## Installation as Part of an App

Apps are full Python packages that can include models, views, static files *and* can include Jobs. They are the best choice for reusable automation. To learn how to create a Nautobot App, check out the [App Development Documentation](../../apps/index.md).

Key requirements:

- Jobs live inside the App's Python module tree
- App dependencies can be managed via `pyproject.toml` or `setup.py`
- Define the Job module path in [`NautobotAppConfig.jobs`](../apps/api/nautobot-app-config.md#nautobotappconfig-code-location-attributes) (defaults to "jobs")
- Use `register_jobs()` to register any included Jobs
- Jobs must be manually enabled before running

Once registered and enabled, Jobs appear in the **Jobs** tab grouped by their App and module metadata.

Example layout:

```text
my_app/
├── __init__.py
├── apps.py
├── jobs/
│   ├── __init__.py
│   ├── cleanup.py
│   └── report.py
└── ...
```

In `apps.py`:

```python
from nautobot.apps.apps import NautobotAppConfig

class MyAppConfig(NautobotAppConfig):
    name = "my_app"
    jobs = "my_app.jobs"
```

In `jobs/__init__.py`:

```python
from nautobot.apps.jobs import register_jobs
from .cleanup import CleanupJob
from .report import ComplianceReport

register_jobs(CleanupJob, ComplianceReport)
```

!!! tip
    For more on App-integrated Jobs, see the [Jobs platform feature](../apps/api/platform-features/jobs.md).
