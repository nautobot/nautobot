"""Custom signals and handlers for the core Nautobot application."""

from django.dispatch import Signal


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
