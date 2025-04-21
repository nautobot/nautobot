## Installing Jobs
<!-- move:installation.md -->
Jobs may be installed in one of three ways:

* Manually installed as files in the [`JOBS_ROOT`](../../user-guide/administration/configuration/settings.md#jobs_root) path (which defaults to `$NAUTOBOT_ROOT/jobs/`).
    * Python files and subdirectories containing Python files will be dynamically loaded at Nautobot startup in order to discover and register available Job classes. For example, a Job class named `MyJobClass` in `$JOBS_ROOT/my_job.py` will be loaded into Nautobot as `my_job.MyJobClass`.
    * All Python modules in this directory are imported by Nautobot and all worker processes at startup. If you have a `custom_jobs.py` and a `custom_jobs_module/__init__.py` file in your `JOBS_ROOT`, both of these files will be imported at startup.
* Imported from an external [Git repository](../../user-guide/platform-functionality/gitrepository.md#jobs).
    * Git repositories are loaded into the module namespace of the `GitRepository.slug` value at startup. For example, if your `slug` value is `my_git_jobs` your Jobs will be loaded into Python as `my_git_jobs.jobs.MyJobClass`.
    * All git repositories providing Jobs must include a `__init__.py` file at the root of the repository.
    * Nautobot and all worker processes will import the git repository's `jobs` module at startup so a `jobs.py` or `jobs/__init__.py` file must exist in the root of the repository.
* Packaged as part of an [App](../apps/api/platform-features/jobs.md).
    * Jobs installed this way are part of the App's Python module and can import code from elsewhere in the App or even have dependencies on other packages, if needed, via the standard Python packaging mechanisms.

In any case, each module holds one or more Job classes (Python classes), each of which serves a specific purpose. The logic of each Job can be split into a number of distinct methods, each of which performs a discrete portion of the overall Job logic.

For example, we can create a module named `device_jobs.py` to hold all of our Jobs which pertain to devices in Nautobot. Within that module, we might define several Jobs. Each Job is defined as a Python class inheriting from `nautobot.apps.jobs.Job`, which provides the base functionality needed to accept user input and log activity.

+/- 2.0.0 "`register_jobs()` must be called"
    All Job classes that are intended to be runnable must now be registered by a call to `nautobot.apps.jobs.register_jobs()` on module import. This allows for a module to, if desired, define "abstract" base Job classes that are defined in code but are not registered (and therefore are not runnable in Nautobot). The `register_jobs` method accepts one or more Job classes as arguments.
