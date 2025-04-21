# Jobs

Jobs are Python scripts executed within Nautobot to automate tasks such as data validation, bulk data changes, external integrations, and more. Before you start writing Jobs, make sure you're familiar with the [core concepts of Jobs](../../user-guide/platform-functionality/jobs/index.md), including the difference between a Job class (Python code) and a Job record (stored in Nautobot's database).

??? tip "Job class source code loading"
    The Job database record does not store the Job's source code. It only records metadata about the existence and configuration of each Job class. The Job class itself is loaded directly from the file system or App package into memory.

    From Nautobot 2.2.3 onward, known Job classes are cached in the [application registry](../core/application-registry.md#jobs), which refreshes at Nautobot startup and just before Job execution. Always retrieve Jobs via the official APIs (`get_job()` and `get_jobs()`) rather than relying on internal caching mechanisms.

The Developer Guide for Jobs is structured into the following subpages:

- **[Getting Started](./getting-started.md)**: Define and register your first Job.
- **[Installing Jobs](./installation.md)**: Ways to distribute Jobs (JOBS_ROOT, Git repositories, and App packaging).
- **[Job Structure](./job-structure.md)**: Learn the anatomy of a Job, including metadata, variables, and execution methods.
- **[Common Job Patterns](./job-patterns.md)**: Implement typical Job functionalities, such as audits, singleton tasks, logging, and file handling.
- **[Testing Jobs](./testing.md)**: Guidance on testing Jobs, including unit tests and debugging with cProfile.
- **[Job Extensions](./job-extensions.md)**: Extend Job capabilities with specialized subclasses like Job Buttons and Job Hooks.
- **[Job Reference](./job-reference.md)**: Reference tables and reserved attribute lists useful when developing Jobs.

For migration guidance from Nautobot v1, refer to the [Migrating Jobs From Nautobot v1](migration/from-v1.md) section.