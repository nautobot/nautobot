"""Simple EventBroker that just emits syslogs."""

import json
import logging

from .base import EventBroker


class SyslogEventBroker(EventBroker):
    def __init__(self, *args, level=logging.INFO, **kwargs):
        """Initialize a SyslogEventBroker that emits logs at the given level."""
        super().__init__(*args, **kwargs)
        self.level = level

    def publish(self, *, topic, payload):
        logger = logging.getLogger(f"nautobot.events.{topic}")
        # Add an indent of 4 to payload
        payload = json.dumps(json.loads(payload), indent=4)
        logger.log(self.level, "%s", payload)
