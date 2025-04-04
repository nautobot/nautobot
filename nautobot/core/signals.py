"""Custom signals and handlers for the core Nautobot application."""

import contextlib
from functools import wraps
import inspect
import logging

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.core.cache import cache
from django.dispatch import receiver, Signal
import redis.exceptions

nautobot_database_ready = Signal()
"""
Signal sent to all installed apps and plugins after the database is ready.

Specifically this is triggered by the Django built-in `post_migrate` signal,
i.e., after `nautobot-server migrate` or `nautobot-server post_upgrade` commands are run.

In other words, this signal is **not** emitted during the actual server execution; rather it is emitted
when setting up the database prior to running the server.

The intended purpose of this signal is for apps and plugins that need to populate or modify the database contents
(**not** the database schema itself!), for example to ensure the existence of certain CustomFields, Jobs,
Relationships, etc.
"""


@receiver(user_logged_in)
def user_logged_in_signal(sender, request, user, **kwargs):
    """Generate a log message when a user logs in through the web ui"""
    logger = logging.getLogger("nautobot.auth.login")
    logger.info(f"User {user} successfully authenticated")


@receiver(user_logged_out)
def user_logged_out_signal(sender, request, user, **kwargs):
    """Generate a log message when a user logs out from the web ui"""
    logger = logging.getLogger("nautobot.auth.logout")
    logger.info(f"User {user} has logged out")


def disable_for_loaddata(signal_handler):
    """
    Return early from the given signal handler if triggered during a `nautobot-server loaddata` call.

    Necessary because for whatever reason, Django's `m2m_changed` signal lacks a `raw` flag and so there's no easy way
    to tell whether any given m2m_changed signal handler is being called from loaddata otherwise.

    Copied shamelessly from https://code.djangoproject.com/ticket/8399#comment:7
    """

    @wraps(signal_handler)
    def wrapper(*args, **kwargs):
        """Return early if loaddata is part of the stack."""
        for fr in inspect.stack():
            if inspect.getmodulename(fr[1]) == "loaddata":
                return
        signal_handler(*args, **kwargs)

    return wrapper


def invalidate_max_depth_cache(sender, **kwargs):
    """
    Clear the appropriate TreeManager.max_depth cache as the create/update/delete may have changed the tree.

    Note that this signal is connected in `TreeModel.__init_subclass__()` so as to only apply to those models.
    """
    from nautobot.core.models.tree_queries import TreeManager

    if not isinstance(sender.objects, TreeManager):
        return

    with contextlib.suppress(redis.exceptions.ConnectionError):
        cache.delete(sender.objects.max_depth_cache_key)
