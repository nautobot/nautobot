import logging

from django.conf import settings
from django.db import connections

LOGGER = logging.getLogger(__name__)


class BranchContext:
    def __init__(self, branch_name=None, using=None, user=None, autocommit=True):
        self.branch_name = branch_name
        self.using = using or "default"
        self.user = user
        self.autocommit = autocommit

    def __enter__(self):
        if self.branch_name is None or "nautobot_version_control" not in settings.PLUGINS:
            if self.branch_name is not None:
                LOGGER.warning(
                    "nautobot_version_control is not installed, ignoring requested branch %s", self.branch_name
                )
            return

        from nautobot_version_control.utils import active_branch  # pylint: disable=import-error

        self.cursor = connections[self.using].cursor()
        self.cursor.__enter__()
        self.original_branch = active_branch(using=self.using)

        if self.branch_name != self.original_branch:
            if self.using == "default":
                LOGGER.debug("Switching to branch %s", self.branch_name)

            self.cursor.execute("CALL dolt_checkout(%s);", [self.branch_name])

            if self.autocommit:
                from nautobot_version_control.middleware import AutoDoltCommit  # pylint: disable=import-error

                self.auto_dolt_commit = AutoDoltCommit(user=self.user)
                self.auto_dolt_commit.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        if self.branch_name is None or "nautobot_version_control" not in settings.PLUGINS:
            return

        if self.branch_name != self.original_branch:
            if self.autocommit:
                self.auto_dolt_commit.__exit__(exc_type, exc_value, traceback)

            self.cursor.execute("CALL dolt_checkout(%s);", [self.original_branch])

            if self.using == "default":
                LOGGER.debug("Returned to branch %s", self.original_branch)

        self.cursor.__exit__(exc_type, exc_value, traceback)
