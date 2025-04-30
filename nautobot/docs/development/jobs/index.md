# Developing Jobs

Jobs are Python classes that define custom automation logic in Nautobot. This guide will help you write, structure, test, and deploy Jobs that run within Nautobot's execution engine.

Before you begin, make sure you're familiar with:

- The [core concepts of Jobs](../../user-guide/platform-functionality/jobs/index.md)
- The [difference between Job classes and Job records](./job-structure.md#job-class-vs-job-record)

??? tip "Where is Job code stored?"
    Nautobot **does not** store Job code in the database. Instead, it loads Python classes from your file system or installed packages. The Job record stores only metadata — like name, description, and enabled state.

## Job Development Workflow

Each of the pages below builds on the previous, from creating a Job to testing it in CI.

- **[Getting Started](./getting-started.md)**  
    Write and run your first Job. Learn the minimum required structure and how to register and enable it in Nautobot.

- **[Installing Jobs](./installation.md)**  
    Choose where your Jobs live: in `JOBS_ROOT`, inside a Git repository, or bundled with a custom Nautobot App. Understand the pros and cons of each.

- **[Job Structure](./job-structure.md)**  
    Define metadata, variables, and the required `run()` method. Learn how Job lifecycle methods work and how input gets passed in.

- **[Common Patterns](./job-patterns.md)**  
    Build Jobs that do more — read files, generate logs, return results, validate data, or act on user input. Includes tested snippets.

- **[Job Extensions](./job-extensions.md)**  
    Go beyond manual runs. Trigger Jobs from the UI (Job Buttons) or automatically on data changes (Job Hooks).

- **[Testing Jobs](./testing.md)**  
    Use Nautobot's `run_job_for_testing()` helper and Django's `TransactionTestCase` to test Jobs like any other Python code. Includes cProfile tips.

## Migrating from Nautobot v1

Jobs in Nautobot v2 use a different structure than those in v1. If you're upgrading existing Jobs, start here:

- [Migrating Jobs from v1](migration/from-v1.md)
