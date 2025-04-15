import logging

from django.conf import settings
from django.db import connections

LOGGER = logging.getLogger(__name__)


class BranchContext:
    def __init__(self, branch_name=None, using=None, user=None, autocommit=True):
        """
        Instantiate a BranchContext context manager.

        Example:
            with BranchContext(branch_name="my-branch", user=request.user):
                ...

        Args:
            branch_name (str): The Dolt branch name (if any) to potentially switch to.
                If left as the default `None`, this context manager does nothing, allowing it to be safely used in
                code that can execute in a non-version-controlled Nautobot deployment as well.
            using (str, list[str]): The database connection alias(es) to potentially switch to the specified branch.
                Note it can be a *list* of connections, or a single connection alias string like most Django built-ins.
                If omitted, only the `"default"` connection will be used.
            user (User): The user account to associate with any Dolt Commit created when using `autocommit=True`.
            autocommit (bool): Whether to create an automatic Dolt Commit record when exiting this context.
        """
        self.branch_name = branch_name
        if not using:
            self.using = ["default"]
        elif isinstance(using, str):
            self.using = [using]
        else:
            self.using = using
        self.user = user
        self.autocommit = autocommit

        self.cursors = {}
        self.original_branches = {}
        self.auto_dolt_commit = None

    def __enter__(self):
        if self.branch_name is None or "nautobot_version_control" not in settings.PLUGINS:
            if self.branch_name is not None:
                LOGGER.warning(
                    "nautobot_version_control is not installed, ignoring requested branch %s", self.branch_name
                )
            return

        from nautobot_version_control.utils import active_branch, checkout_branch  # pylint: disable=import-error

        for using in self.using:
            self.cursors[using] = connections[using].cursor()
            self.cursors[using].__enter__()
            self.original_branches[using] = active_branch(using=using)

            if self.branch_name != self.original_branches[using]:
                LOGGER.info("Switching connection %r to branch %r", using, self.branch_name)

                checkout_branch(self.branch_name, using=using)

        if self.autocommit:
            from nautobot_version_control.middleware import AutoDoltCommit  # pylint: disable=import-error

            self.auto_dolt_commit = AutoDoltCommit(user=self.user)
            self.auto_dolt_commit.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        if self.branch_name is None or "nautobot_version_control" not in settings.PLUGINS:
            return

        if self.autocommit:
            self.auto_dolt_commit.__exit__(exc_type, exc_value, traceback)

        for using in self.using:
            if self.branch_name != self.original_branches[using]:
                from nautobot_version_control.utils import checkout_branch  # pylint: disable=import-error

                checkout_branch(self.original_branches[using], using=using)

                LOGGER.info("Returned connection %r to branch %r", using, self.original_branches[using])

            self.cursors[using].__exit__(exc_type, exc_value, traceback)
