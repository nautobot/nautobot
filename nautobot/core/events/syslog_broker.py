"""Simple EventBroker that just emits syslogs."""

import json
import logging

from .base import EventBroker


class SyslogEventBroker(EventBroker):
    def __init__(self, *, level=logging.INFO):
        """Initialize a SyslogEventBroker that emits logs at the given level."""
        self.level = level

    def publish(self, *, topic, payload):
        logger = logging.getLogger(f"nautobot.events.{topic}")
        logger.log(self.level, "%s", json.dumps(payload, indent=4))
