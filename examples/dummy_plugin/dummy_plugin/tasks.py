"""
Example tasks used for baseline testing.
"""

import time

from nautobot.core.celery import nautobot_task


@nautobot_task(once={"keys": []})
def slow_add(a, b, interval=5):
    """Add `a` and `b` after `interval` expires."""
    time.sleep(interval)
    return a + b
