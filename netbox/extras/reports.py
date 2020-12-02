"""Legacy implementation of "reports" API. New development should use extras.custom_jobs instead."""
from .custom_jobs import (
    CustomJob,
)


class Report(CustomJob):
    """
    NetBox users can extend this object to write custom reports to be used for validating data within NetBox. Each
    report must have one or more test methods named `test_*`.

    The `_results` attribute of a completed report will take the following form:

    {
        'test_bar': {
            'failures': 42,
            'log': [
                (<datetime>, <level>, <object>, <message>),
                ...
            ]
        },
        'test_foo': {
            'failures': 0,
            'log': [
                (<datetime>, <level>, <object>, <message>),
                ...
            ]
        }
    }
    """

    def __init__(self):
        super().__init__()

        if not self.test_methods:
            raise Exception("A report must contain at least one test method.")

    def log_success(self, obj, message=None):
        """
        Record a successful test against an object. Logging a message is optional.
        """
        super().log_success(obj=obj, message=message)

    def log_info(self, obj, message):
        """
        Log an informational message.
        """
        super().log_info(obj=obj, message=message)

    def log_warning(self, obj, message):
        """
        Log a warning.
        """
        super().log_warning(obj=obj, message=message)

    def log_failure(self, obj, message):
        """
        Log a failure. Calling this method will automatically mark the report as failed.
        """
        super().log_failure(obj=obj, message=message)
