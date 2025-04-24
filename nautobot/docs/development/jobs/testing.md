# Testing Jobs

Jobs are regular Python classes and can be tested using [Django’s standard test utilities](https://docs.djangoproject.com/en/stable/topics/testing/). However, since Jobs are run through Celery and rely on specific setup (like enabling the Job in the database), Nautobot provides additional helpers to make testing easier and more realistic.

While individual methods within your Job can and should be tested in isolation, you'll likely also want to test the entire execution of the Job.

### Using `TransactionTestCase`

Nautobot provides a subclass of Django’s `TransactionTestCase` that is tailored for testing Jobs. This test class ensures each test starts with a clean database and supports integration with Nautobot’s Job system.

Use `nautobot.apps.testing.TransactionTestCase` instead of `django.test.TestCase`, especially when invoking full Job execution via `run_job_for_testing()`. 

!!! tip "Why `TransactionTestCase`?"
    `TransactionTestCase` allows database changes to persist across the Celery task boundary when testing, which is required because Jobs are executed in a different process context.
    (Refer to the [Django documentation](https://docs.djangoproject.com/en/stable/topics/testing/tools/#provided-test-case-classes) if you're interested in the differences between these classes - `TransactionTestCase` from Nautobot is a small wrapper around Django's `TransactionTestCase`).

When using `TransactionTestCase` (whether from Django or from Nautobot) each test runs on a completely empty database. Furthermore, Nautobot requires new Jobs to be enabled before they can run. Therefore, we need to make sure the Job is enabled before each run which `run_job_for_testing` handles for us.

### Running a Job in a Test

Nautobot provides the `run_job_for_testing()` utility to simplify test execution. It handles Job registration, enables the Job if needed, and executes it with your provided input variables using the standard Celery worker system.

!!! tip "What `run_job_for_testing()` Does"
    This helper:
    - Enables the Job in the database if not already enabled
    - Executes it with the provided variables
    - Returns a `JobResult` object for inspection

A simple example of a Job test case might look like the following:

```python
from nautobot.apps.testing import run_job_for_testing, TransactionTestCase
from nautobot.extras.models import Job, JobLogEntry


class MyJobTestCase(TransactionTestCase):
    def test_my_job(self):
        # Testing of Job "MyJob" in file "my_job_file.py" in $JOBS_ROOT
        job = Job.objects.get(job_class_name="MyJob", module_name="my_job_file")
        # or, job = Job.objects.get_for_class_path("local/my_job_file/MyJob")
        job_result = run_job_for_testing(job, var1="abc", var2=123)

        # Inspect the logs created by running the job
        log_entries = JobLogEntry.objects.filter(job_result=job_result)
        for log_entry in log_entries:
            self.assertEqual(log_entry.message, "...")
```

The test files should be placed under the `tests` folder in the app's directory or under `JOBS_ROOT`. 

!!! tip "Running Tests"
    You can run Job tests using either Django’s test runner or `pytest`, depending on your environment:
    
    - `nautobot-server test myapp.tests.test_jobs`
    - `pytest myapp/tests/test_jobs.py`

    If your test file lives in `JOBS_ROOT`, make sure the `JOBS_ROOT` environment variable is set.

!!! tip
    For more advanced examples refer to the Nautobot source code, specifically `nautobot/extras/tests/test_jobs.py`.

## Debugging Job Performance

Debugging the performance of Nautobot Jobs can be tricky, because they are executed in the Celery worker context. In order to gain extra visibility, [cProfile](https://docs.python.org/3/library/profile.html) can be used to profile the Job execution.

The 'profile' form field on Jobs is automatically available when the `DEBUG` settings is `True`. When you select that checkbox, a profiling report in the pstats format will be written to the file system of the environment where the Job runs. Normally, this is on the file system of the worker process, but if you are using the `nautobot-server runjob` command with `--local`, it will end up in the file system of the web application itself. The path of the written file will be logged in the Job.

!!! note
    If you need to run this in an environment where `DEBUG` is `False`, you have the option of using `nautobot-server runjob` with the `--profile` flag. According to the docs, `cProfile` should have minimal impact on the performance of the Job; still, proceed with caution when using this in a production environment.

### Reading Profiling Reports

Profiling files are saved in the format expected by Python’s `pstats` module. A full description on how to deal with the output of `cProfile` can be found in the [Instant User's Manual](https://docs.python.org/3/library/profile.html#instant-user-s-manual). You can analyze them as follows:

```python
import pstats
job_result_uuid = "66b70231-002f-412b-8cc4-1cc9609c2c9b"
stats = pstats.Stats(f"/tmp/nautobot-jobresult-{job_result_uuid}.pstats")
stats.sort_stats(pstats.SortKey.CUMULATIVE).print_stats(10)
```

This prints the 10 functions where the Job spent the most time. You can customize the sort key and output to focus on specific bottlenecks.