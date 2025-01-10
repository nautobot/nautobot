"""Base classes for Nautobot event notification framework."""

from abc import ABC, abstractmethod


class EventBroker(ABC):
    """Abstract base class for concrete implementations of event brokers such as syslog, Redis, Kafka, etc."""

    def __init__(self, *args, include_topics=None, exclude_topics=None, **kwargs) -> None:
        self.include_topics = include_topics or ["*"]
        self.exclude_topics = exclude_topics or []
        super().__init__(*args, **kwargs)

    @abstractmethod
    def publish(self, *, topic, payload):
        """
        Possibly publish the given data `payload` to the given event `topic`.

        Args:
            topic (str): Topic identifier.
                Convention is to use snake_case and use periods to delineate related groups of topics,
                similar to Python logger naming. For example, you might receive topics such as `create.dcim.device`,
                `update.dcim.device`, `delete.dcim.device`, `create.dcim.interface`, `create.ipam.ipaddress`, etc.
            payload (dict): JSON-serializable structured data to publish.
                While not all EventBrokers may actually use JSON as their data format, it makes for a reasonable
                lowest common denominator for serializability.
        """
