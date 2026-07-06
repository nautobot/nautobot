# Instrumenting Your App with OpenTelemetry

Nautobot ships optional [OpenTelemetry](https://opentelemetry.io/) instrumentation (see the [OpenTelemetry administration guide](../../../../user-guide/administration/guides/opentelemetry.md) for how an operator enables and configures it). When it is enabled, Nautobot configures the global OpenTelemetry tracer and meter providers at startup, so any code your app, Job, or SSoT plugin runs can add its own spans, metrics, and log correlation with no additional wiring - the data flows to the same collector and backends the operator already configured.

This page describes how to instrument your own code to understand execution flow, participate in distributed traces, and measure performance so you know where to focus optimization efforts.

!!! note
    Instrumentation is opt-in and off by default. The global providers are always safe to call: when telemetry is disabled the OpenTelemetry API uses no-op providers, so the calls below add negligible overhead and require no feature-detection in your code.

## Tracing a Block of Code

Nautobot exposes a `traced_span` context manager that wraps the standard tracer boilerplate. Import it from the public `nautobot.apps.utils` API:

```python
from nautobot.apps.utils import traced_span


def get_expensive_thing(self, obj):
    with traced_span(
        "my_app.services",
        "expensive_thing.get",
        **{"expensive_thing.model": obj._meta.label_lower},
    ) as span:
        result = cache.get(obj.pk)
        span.set_attribute("expensive_thing.hit", result is not None)
        if result is None:
            result = self._compute(obj)
        return result
```

- The first argument is the tracer name, conventionally your dotted module namespace (for example `"my_app.services"`).
- The second is the span name.
- Keyword arguments become span attributes set immediately; `None` values are skipped. You can set more attributes conditionally on the yielded span (for example a cache `hit` boolean once the result is known).

Follow the same convention Nautobot core uses: **prefix attribute keys with the span name** (a `expensive_thing.get` span uses `expensive_thing.*` attributes) so traces stay easy to query and filter.

For full control - custom span kinds, links, or events - use the OpenTelemetry API directly. Because Nautobot sets the global tracer provider at startup, `trace.get_tracer(...)` returns a tracer bound to the configured provider automatically:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("my_app.sync") as span:
    span.set_attribute("my_app.record_count", len(records))
    ...
```

## Participating in Distributed Traces

You do not need to propagate context manually within a single Nautobot process: spans you open with `traced_span` or `start_as_current_span` automatically nest under whatever span is already active (for example the HTTP request span created by Nautobot's Django instrumentation, or a Celery task span for a running Job). This is what lets a single trace span the web request, the Job execution, and the database calls beneath them.

If your app makes outbound HTTP calls with the `requests` library, Nautobot's `RequestsInstrumentor` already injects the `traceparent` header, so a downstream service that understands OpenTelemetry can continue the same trace. For other client libraries, see [Auto-instrumenting a Library](#auto-instrumenting-a-library) below.

## Instrumenting Jobs and SSoT

A Job's `run()` method executes inside a Celery task span, so wrapping meaningful phases of your Job in spans slots them directly into the task's trace - ideal for seeing which phase dominates runtime:

```python
from nautobot.apps.jobs import Job, register_jobs
from nautobot.apps.utils import traced_span


class SyncDevices(Job):
    def run(self, *args, **kwargs):
        with traced_span("my_app.jobs", "sync_devices.load"):
            records = self._load_source()
        with traced_span("my_app.jobs", "sync_devices.reconcile") as span:
            span.set_attribute("sync_devices.record_count", len(records))
            self._reconcile(records)


register_jobs(SyncDevices)
```

`nautobot-ssot` synchronization jobs are ordinary Nautobot Jobs, so the same pattern applies - wrap the load, diff, and sync phases of your adapter in spans to see where a sync spends its time.

When log correlation is enabled by the operator (the `OTEL_PYTHON_LOG_CORRELATION` setting), messages emitted through `self.logger` inside a Job are automatically tagged with the active trace and span IDs, so Job log entries can be correlated with the surrounding trace.

## Measuring Performance with Metrics

To record counters, histograms, or other metrics, obtain a meter from the global meter provider (configured by Nautobot at startup) and create instruments once at module scope:

```python
from opentelemetry import metrics

meter = metrics.get_meter(__name__)
sync_counter = meter.create_counter(
    "my_app.syncs",
    description="Number of sync runs.",
)
records_histogram = meter.create_histogram(
    "my_app.records_processed",
    description="Records processed per sync run.",
)


def run_sync(records):
    sync_counter.add(1, {"result": "started"})
    records_histogram.record(len(records))
    ...
```

Metrics are exported only when the operator has enabled a metrics exporter; otherwise these calls are no-ops. Use tracing to find *where* time goes on a single request or Job, and metrics to track *trends* (rates, distributions) across many runs so you know what to focus improvement efforts on.

!!! note
    Nautobot also exposes Prometheus metrics through a separate mechanism; see [Prometheus Metrics](../prometheus.md) if you want to expose app metrics on the Nautobot `/metrics` endpoint instead of through the OpenTelemetry pipeline.

## Auto-instrumenting a Library

If your app depends on a library that has an OpenTelemetry instrumentor (for example `botocore`, `elasticsearch`, or another database client), enable it from your `NautobotAppConfig.ready()` method. `ready()` runs after Nautobot has set the global tracer provider, so calling the instrumentor with no arguments binds it to Nautobot's provider:

```python
from nautobot.apps import NautobotAppConfig


class MyAppConfig(NautobotAppConfig):
    name = "my_app"

    def ready(self):
        super().ready()
        from django.conf import settings

        if settings.OTEL_PYTHON_DJANGO_INSTRUMENT:
            from opentelemetry.instrumentation.botocore import BotocoreInstrumentor

            BotocoreInstrumentor().instrument()
```

- Guard the call on `settings.OTEL_PYTHON_DJANGO_INSTRUMENT` so your app only instruments when the operator has enabled telemetry.
- Do not call `trace.set_tracer_provider()` yourself - the provider can only be set once per process, and Nautobot has already set it. Your app's job is only to enable its instrumentor against the existing global provider.
- Most client-library instrumentors patch at call time, so enabling them in `ready()` is early enough to capture calls your Jobs and views make later.

## Trying It Locally

The development environment ships an opt-in local observability stack (OpenTelemetry Collector, Tempo, Mimir, Loki, and Grafana) for viewing the traces, metrics, and logs your instrumentation emits. See [Local Observability Stack](../../../core/docker-compose-advanced-use-cases.md#local-observability-stack) for how to enable it and open Grafana.
