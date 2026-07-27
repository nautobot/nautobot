"""Base classes and data structures for Nautobot event consumer framework."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterator, List


@dataclass
class ConsumedEvent:
    """A single event received from an external broker by an EventConsumer.

    Attributes:
        topic (str): The topic identifier of the event (e.g., ``nautobot.create.dcim.device``).
        payload (dict): The deserialized event payload. Expected to be JSON-compatible.
        headers (dict): Optional broker headers or metadata associated with the event.
        broker_ref (Any): Opaque handle owned by the consumer, used internally for ack/nack
            (e.g., a delivery tag, a Kafka offset, a Pub/Sub message id). Callers outside the
            consumer should treat this field as opaque.
    """

    topic: str
    payload: dict
    headers: dict = field(default_factory=dict)
    broker_ref: Any = None


class EventConsumer(ABC):
    """Abstract base class for concrete implementations of event consumers.

    An ``EventConsumer`` is the receive-side counterpart to ``EventBroker``. A consumer
    subscribes to one or more topics on an external system (Redis, Kafka, NATS, Azure Service
    Bus, etc.), reads events from it, and yields them to a worker that dispatches matching
    ``EventConsumerJob`` subclasses.

    Subclasses MUST implement ``subscribe()``, ``read()``, ``ack()``, and ``nack()``. The
    ``close()`` method has a default no-op implementation and can be overridden if a clean
    shutdown sequence is required by the underlying client.

    ``include_topics`` and ``exclude_topics`` use the same fnmatch-based glob semantics as
    ``EventBroker`` — they are filters applied at dispatch time, in addition to whatever
    native subscription mechanism the broker exposes.
    """

    def __init__(self, *args, include_topics=None, exclude_topics=None, **kwargs) -> None:
        self.include_topics = include_topics or ["*"]
        self.exclude_topics = exclude_topics or []
        super().__init__(*args, **kwargs)

    @abstractmethod
    def subscribe(self, topics: List[str]) -> None:
        """Subscribe to the given list of topic patterns.

        Implementations should translate the supplied glob-style patterns into whatever
        subscription primitive the underlying broker exposes (PSUBSCRIBE, consumer group
        subscription, etc.).
        """

    @abstractmethod
    def read(self) -> Iterator[ConsumedEvent]:
        """Yield ``ConsumedEvent`` objects as they arrive from the broker.

        This method is expected to block until either a message arrives or ``close()`` is
        called. It runs in a worker thread spawned by the ``run_event_consumers`` management
        command and is iterated until shutdown is requested.
        """

    @abstractmethod
    def ack(self, event: ConsumedEvent) -> None:
        """Acknowledge successful handoff of ``event`` to Nautobot's Job machinery.

        Called by the worker once a matching Job has been successfully enqueued. For
        brokers without an acknowledgement concept (e.g., Redis Pub/Sub) this should be a
        no-op.
        """

    @abstractmethod
    def nack(self, event: ConsumedEvent, requeue: bool = True) -> None:
        """Reject ``event`` because Nautobot could not enqueue a matching Job.

        Called by the worker when ``JobResult.enqueue_job`` raises (e.g., the database is
        unavailable, no matching ``Job`` record exists for the bound class path). If
        ``requeue`` is ``True`` and the broker supports it, the event should be redelivered.
        """

    def close(self) -> None:
        """Clean shutdown. Default implementation is a no-op.

        Subclasses with persistent connections, background threads, or buffered state
        should override this to release resources. Called from the ``run_event_consumers``
        signal handler when ``SIGTERM`` or ``SIGINT`` is received.
        """
