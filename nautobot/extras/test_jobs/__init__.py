def load_tests(*args):
    """Implement unittest discovery for this submodule as a no-op.

    This prevents unittest from recursively loading all of the modules under this directory to inspect whether they
    define test cases. This is necessary because otherwise the `jobs_module` submodule will get loaded when tests run,
    which will in turn call `register_jobs()`, incorrectly/unexpectedly registering the test Job defined in that module
    as if it were a system Job, which will cause tests to fail due to the unexpected presence of this Job.
    """
