from contextlib import contextmanager
import logging

from django.conf import settings
from django.db import transaction

LOGGER = logging.getLogger(__name__)


@contextmanager
def maybe_with_branch(branch_name=None, using=None):
    """Possibly wrap some code in a Version Control branch-aware transaction, or gracefully just run the code."""
    if branch_name is None or "nautobot_version_control" not in settings.PLUGINS:
        if branch_name is not None:
            LOGGER.warning("nautobot_version_control is not installed, ignoring requested branch %s", branch_name)
        yield
        return

    from nautobot_version_control.utils import query_on_branch

    if using is not None:
        with transaction.atomic(using=using):
            with query_on_branch(branch_name):
                yield
    else:
        with query_on_branch(branch_name):
            yield
