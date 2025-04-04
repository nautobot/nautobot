"""Simple EventBroker for publishing events to Redis.

To verify that an instance of this broker is working, you can do the following in `nautobot-server nbshell`:

```python
import json

import redis


connection = redis.StrictRedis(host="redis", port=6379, db=2, password="...", charset="utf-8", decode_responses=True)


def listen():
    sub = connection.pubsub()
    sub.psubscribe("nautobot.*")
    for message in sub.listen():
        if message["type"] == "pmessage":
            print(f"Got a pmessage on channel {message['channel']}")
            print(json.dumps(json.loads(message["data"]), indent=2))


listen()
```

Then perform any action that triggers an event, such as creating or updating a record through the Nautobot UI.
"""

import redis

from .base import EventBroker


class RedisEventBroker(EventBroker):
    """EventBroker for publishing events to Redis."""

    def __init__(self, *args, url, **kwargs):
        """Initialize and configure a RedisEventBroker.

        Args:
            url (str): The Redis URL to connect to.
        """
        self.url = url
        self.connection = redis.StrictRedis.from_url(self.url)
        super().__init__(*args, **kwargs)

    def publish(self, *, topic, payload):
        self.connection.publish(topic, payload)
