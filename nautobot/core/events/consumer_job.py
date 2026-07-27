"""``EventConsumerJob`` base class for the event consumer framework.

This module is intentionally **not** imported eagerly from ``nautobot.core.events``.
The Job framework (``nautobot.extras.jobs``) already imports ``publish_event`` from
``nautobot.core.events``, so a top-level import here would create a circular dependency.
``nautobot.core.events.__init__`` exposes ``EventConsumerJob`` via module-level
``__getattr__`` (PEP 562) to defer the import until first access — by which point Django
is fully initialized.
"""

from nautobot.apps.jobs import Job


class EventConsumerJob(Job):
    """Abstract base class for Jobs that process events consumed from external brokers.

    The ``run_event_consumers`` command spreads the consumed event's ``payload`` as this
    Job's keyword arguments — i.e. the payload is expected to be a mapping of input-variable
    names to values. Subclasses therefore declare their own Job ``Var`` fields matching the
    payload keys (exactly as a normal Job would) and override ``process_event()`` to handle
    them. The event envelope (topic, headers, source-consumer name) is intentionally **not**
    passed through; only the payload reaches the Job.

    The base class still provides standard ``self.logger`` logging, ``JobResult``
    persistence and UI visibility, and permission integration via the user resolved from the
    configured ``SecretsGroup``.

    This base class is **not** registered with the Jobs registry (its ``Meta.hidden`` is
    ``True`` and it is never passed to ``register_jobs()``), so it does not appear in the
    Jobs UI by itself. Subclasses must be registered normally via ``register_jobs(...)``.
    """

    class Meta:
        hidden = True
        has_sensitive_variables = False
        description = "Abstract base for Jobs invoked by the event-consumer framework."

    def run(self, **kwargs):  # pylint: disable=arguments-differ
        """Delegate to ``process_event``.

        The keyword arguments are the consumed event's ``payload`` spread out by the
        ``run_event_consumers`` command. Override ``process_event`` instead of ``run``
        unless you need to customize the full Job lifecycle.
        """
        return self.process_event(**kwargs)

    def process_event(self, **kwargs):
        """Handle a single consumed event. Subclasses MUST override this method.

        Args:
            **kwargs: The consumed event's ``payload``, mapped to the Job's input variables.
        """
        raise NotImplementedError(f"{type(self).__name__} must implement process_event() to handle events")
