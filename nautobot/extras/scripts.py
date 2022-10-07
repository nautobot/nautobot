"""Legacy implementation of "scripts" API. New development should use extras.jobs instead."""
# 2.0 TODO: remove this entire file.
from .jobs import (
    BaseJob,
    Job,
    BooleanVar,
    ChoiceVar,
    FileVar,
    IntegerVar,
    IPAddressVar,
    IPAddressWithMaskVar,
    IPNetworkVar,
    MultiChoiceVar,
    MultiObjectVar,
    ObjectVar,
    StringVar,
    TextVar,
)

__all__ = [
    "BaseScript",
    "BooleanVar",
    "ChoiceVar",
    "FileVar",
    "IntegerVar",
    "IPAddressVar",
    "IPAddressWithMaskVar",
    "IPNetworkVar",
    "MultiChoiceVar",
    "MultiObjectVar",
    "ObjectVar",
    "Script",
    "StringVar",
    "TextVar",
]

#
# Scripts
#


class BaseScript(BaseJob):
    """
    Base model for custom scripts. User classes should inherit from this model if they want to extend Script
    functionality for use in other subclasses.
    """

    def run(self, data, commit):
        raise NotImplementedError("The script must define a run() method.")

    # Logging
    # These APIs are intentionally different in their signature from BaseJob.log_*, because
    # in NetBox, the Script logging APIs were different from the Report logging APIs.
    # pylint: disable=arguments-differ

    def log_success(self, message):
        super().log_success(obj=None, message=message)

    def log_info(self, message):
        super().log_info(obj=None, message=message)

    def log_warning(self, message):
        super().log_warning(obj=None, message=message)

    def log_failure(self, message):
        super().log_failure(obj=None, message=message)


class Script(BaseScript, Job):
    """
    Classes which inherit this model will appear in the list of available scripts.
    """
