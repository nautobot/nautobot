"""``EventConsumerJob`` base class for the event consumer framework.

This module is intentionally **not** imported eagerly from ``nautobot.core.events``.
The Job framework (``nautobot.extras.jobs``) already imports ``publish_event`` from
``nautobot.core.events``, so a top-level import here would create a circular dependency.
``nautobot.core.events.__init__`` exposes ``EventConsumerJob`` via module-level
``__getattr__`` (PEP 562) to defer the import until first access — by which point Django
is fully initialized.
"""

from nautobot.apps.jobs import Job, JSONVar, StringVar


class EventConsumerJob(Job):
    """Abstract base class for Jobs that process events consumed from external brokers.

    Apps subclass this and override ``process_event()``. The framework handles wiring the
    event topic, payload, headers, and source-consumer name into Job kwargs; standard
    ``self.logger`` logging; ``JobResult`` persistence and UI visibility; and permission
    integration via the user resolved from the configured ``SecretsGroup``.

    This base class is **not** registered with the Jobs registry (its ``Meta.hidden`` is
    ``True`` and it is never passed to ``register_jobs()``), so it does not appear in the
    Jobs UI by itself. Subclasses must be registered normally via ``register_jobs(...)``.
    """

    class Meta:
        hidden = True
        has_sensitive_variables = False
        description = "Abstract base for Jobs invoked by the event-consumer framework."

    topic = StringVar(description="Event topic that triggered this Job")
    payload = JSONVar(description="Event payload as published by the source broker")
    headers = JSONVar(description="Event headers / metadata", required=False, default=dict)
    source_consumer = StringVar(
        description="Name of the registered EventConsumer that received this event",
        required=False,
    )

    def run(self, *, topic, payload, headers=None, source_consumer=None):  # pylint: disable=arguments-differ
        """Delegate to ``process_event``.

        Override ``process_event`` instead of ``run`` unless you need to customize the
        full Job lifecycle.
        """
        return self.process_event(
            topic=topic,
            payload=payload,
            headers=headers or {},
            source_consumer=source_consumer,
        )

    def process_event(self, *, topic, payload, headers, source_consumer):
        """Handle a single consumed event. Subclasses MUST override this method."""
        raise NotImplementedError(f"{type(self).__name__} must implement process_event() to handle events")
