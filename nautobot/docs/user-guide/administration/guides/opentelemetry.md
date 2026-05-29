# OpenTelemetry

+++ 3.2.0

Nautobot supports optionally exposing logs, traces, and metrics via [OpenTelemetry](https://opentelemetry.io/).

## Install

See the [Install Guide](../configuration/opentelemetry.md) for installation instructions.

## Instrumentation Layers

Nautobot's OpenTelemetry support is structured in layers. Each layer can be enabled or disabled independently, allowing administrators to balance observability value against performance impact.

| Layer | Controls | Default |
| --- | --- | --- |
| Distributed tracing (requests + logging) | `OTEL_PYTHON_DJANGO_INSTRUMENT` | `False` |
| Log correlation (trace/span IDs in logs) | `OTEL_PYTHON_LOG_CORRELATION` | `True` (when tracing enabled) |
| Database query spans | Always on when tracing is enabled | - |
| Redis command spans | Always on when tracing is enabled | - |
| Celery job spans | Always on when tracing is enabled | - |
| Outbound HTTP propagation | Always on when tracing is enabled | - |
| Trace export | `OTEL_TRACES_EXPORTER` | `otlp` |
| Metrics export | `OTEL_METRICS_EXPORTER` | `otlp` |

### Layer 1 - Distributed tracing

Setting `OTEL_PYTHON_DJANGO_INSTRUMENT=True` activates the core instrumentation layer. This enables:

- **HTTP request tracing** - A span is created for every HTTP request, including path, method, status code, and username. The `traceparent` W3C header is read from incoming requests, allowing Nautobot to participate in a distributed trace originating from an upstream service.
- **Log correlation** - When `OTEL_PYTHON_LOG_CORRELATION=True`, trace and span IDs are injected into every log record, making it possible to correlate logs to the trace that produced them.
- **GraphQL request tracing** - Requests to `/graphql` and `/api/graphql` receive additional spans with the full query document, operation type, and variables.
- **Database query spans** - Every SQL query is captured as a child span with the query text and SQL commenter annotations.
- **Redis command spans** - Every Redis command is captured as a child span.
- **Celery job spans** - Task dispatch and execution are traced. Trace context is propagated from the web request into the async job, linking them in the same trace.
- **Outbound HTTP propagation** - Outgoing HTTP requests made by Nautobot (webhooks, SSoT data sources, etc.) carry the `traceparent` header, stitching downstream services into the same trace.

This layer has the highest value-to-cost ratio. Database and Redis spans in particular are useful for identifying N+1 query patterns and slow cache operations.

### Layer 2 - Metrics export

Metrics are exported via OTLP when `OTEL_METRICS_EXPORTER` is set to `otlp`. Set it to `none` to disable metrics export entirely without affecting tracing.

Metrics export runs on a background thread and does not block requests. However, at high concurrency, the periodic export adds background CPU and network overhead. Disabling metrics export is a low-cost way to reduce collector load while retaining full trace visibility.

### Layer 3 - Trace export

Traces are exported when `OTEL_TRACES_EXPORTER` is set to `otlp`. Set it to `none` to disable export while retaining span creation and log correlation. This is useful for:

- Development environments where collector infrastructure is not available.
- Evaluating the cost of span creation in isolation from export overhead.

#### Trace sampling

Sampling reduces the volume of traces exported without disabling instrumentation. Nautobot does not configure a sampler directly - sampling is best applied at the collector to avoid changing Nautobot's configuration. The OpenTelemetry Collector supports head-based sampling via the `probabilistic_sampler` processor and tail-based sampling via the `tail_sampling` processor.

To configure sampling at the collector, add a processor to the `otel-collector.yaml` pipeline:

```yaml
processors:
  # Sample 20% of traces - adjust rate to suit your data volume
  probabilistic_sampler:
    sampling_percentage: 20

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [probabilistic_sampler]
      exporters: [otlp]
```

Tail-based sampling is more powerful - it allows decisions based on trace attributes such as error status or duration:

```yaml
processors:
  tail_sampling:
    decision_wait: 10s
    policies:
      # Always keep error traces
      - name: errors
        type: status_code
        status_code: {status_codes: [ERROR]}
      # Always keep slow traces (>2s)
      - name: slow-requests
        type: latency
        latency: {threshold_ms: 2000}
      # Sample 5% of everything else
      - name: default
        type: probabilistic
        probabilistic: {sampling_percentage: 5}
```

## Configuration

OpenTelemetry logs, traces, and metrics are not exposed by default. To enable this, the `OTEL_PYTHON_DJANGO_INSTRUMENT` setting should be set to `True`. This will do two things:

- Logs will be exposed in the OpenTelemetry format and include the Trace ID, Span ID, and Resource attributes.
- Metrics and Traces will be exported via OTLP by default.

### Logs

When enabling OpenTelemetry, the logs sent to stdout will have additional information added.

Without OpenTelemetry enabled, logs look like:

```bash
nautobot-nautobot-1       | 04:11:42.768 INFO    django.server :
nautobot-nautobot-1       |   "GET /health/ HTTP/1.1" 200 11469
```

**With** OpenTelemetry enabled, logs look like:

```bash
nautobot-nautobot-1       | 14:06:51,776 INFO [django.server] [basehttp.py:212]
nautobot-nautobot-1       | [trace_id=0 span_id=0 resource.service.name=nautobot
nautobot-nautobot-1       | trace_sampled=False] - "GET /health/ HTTP/1.1" 200 15925

```

### Exporting traces and metrics via OTLP

Traces and metrics are exported via OTLP (OpenTelemetry Protocol) by default.

Once those are set, you need to specify the OTLP endpoint via the `OTEL_EXPORTER_OTLP_ENDPOINT` setting. If necessary, you can set the OTLP protocol via `OTEL_EXPORTER_OTLP_PROTOCOL` to either `grpc` (default) or `http`. If setting to `grpc`, you can also send the metrics insecurely by setting `OTEL_EXPORTER_OTLP_INSECURE` to `True`.

## Receiving OTLP Data

The OTLP collector is outside of the Nautobot scope. Common open source collectors include the [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/) and [Grafana Agent](https://grafana.com/docs/agent/latest/).

### Sample Tracing and Metric Pipeline Configuration

The Nautobot development folder has a sample configuration of using the OpenTelemetry Collector that forwards to [Grafana Tempo](https://grafana.com/oss/tempo/) and [Grafana Mimir](https://grafana.com/oss/mimir/).

The `docker-compose.observability.yml` file has all of the items necessary to start observing logs, traces, and metrics. All of the necessary config files for Grafana, Mimir, OTEL, Promtail, and Tempo are included as well.

### Viewing trace hierarchies

The `console` trace exporter (`OTEL_TRACES_EXPORTER=console`) emits each span as a flat, individual JSON object to stdout as it completes. Spans are not nested - the parent-child relationship is encoded via the `parent_id` field on each span object. This format is useful for confirming that spans are being emitted, but it does not produce a tree view.

To see the full nested waterfall hierarchy (HTTP request span containing the GraphQL span, with database and Redis child spans beneath it), send traces to a visualization backend such as Grafana Tempo via the OTLP exporter. Tempo reconstructs the tree from the `parent_id` references and displays it as a familiar trace waterfall. The development observability stack described above provides this out of the box.

## Security Considerations

### Sensitive data in spans and logs

Several instrumentation layers record request and query content. The values are captured verbatim, both as span attributes (exported to the trace backend) and, for GraphQL, in a structured INFO log entry:

- **GraphQL** - The `graphql.document` (full query text) and `graphql.variables` attributes are recorded for every request to `/graphql` and `/api/graphql`. Nautobot's GraphQL schema is read-only, so secret *values* stored in Nautobot are not submitted by clients. However, the query document and variables still contain user-supplied **filter and search terms** (for example, `secrets(name: "prod-db-root-password")` or a `q` search string). These terms may themselves be sensitive, and apps that register custom GraphQL mutations would have their input arguments captured here as well.
- **Database** - The `db.statement` attribute on every SQL query span contains the full query text, including literal values bound into the statement.

If telemetry is routed to an external backend, account for this in your data-handling and retention policy.

OpenTelemetry does not provide a single SDK setting to globally redact attribute values; the vendor-neutral approach is to filter at the collector before export. The OpenTelemetry Collector provides four standard processors for this:

- `attributes` - remove, hash, or modify specific named attributes.
- `redaction` - delete all attributes *except* those on an allow-list.
- `filter` - drop entire spans, logs, or metrics matching a condition.
- `transform` - rewrite values with regular expressions (for example, masking patterns that look like tokens).

For example, to strip GraphQL variables and hash the SQL statement before export, add an `attributes` processor to the `otel-collector.yaml` traces pipeline:

```yaml
processors:
  attributes:
    actions:
      - key: graphql.variables
        action: delete
      - key: db.statement
        action: hash

service:
  pipelines:
    traces:
      processors: [attributes]
```

As a coarse, SDK-side safety net you can also cap how much of any single attribute value is recorded by setting the standard `OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT` environment variable (an integer character limit; unlimited by default). This truncates long values such as large query documents before they leave the process, but it does not selectively redact - use collector-side processors for targeted redaction.

### Outbound propagation to untrusted services

`RequestsInstrumentor` adds a `traceparent` header to all outgoing HTTP requests made by Nautobot. For most integrations this is harmless - external services that do not understand `traceparent` ignore it. However, if outbound requests target untrusted external services, the header leaks that the request is part of a trace. This is generally low-risk but worth being aware of in high-security environments.

### Collector availability

If the OTLP endpoint is unreachable, the `BatchSpanProcessor` retries and then silently drops spans after the queue fills. Nautobot does not surface export failures in the UI or via alerts. Operators should monitor collector health independently - a down collector means telemetry data is silently lost, not that Nautobot is impacted.

### Data retention

Celery job traces are linked to the originating web request via trace context propagation. This means the trace backend contains a record associating a user's request to the jobs it triggered. Review your trace backend's retention policy to ensure it aligns with your data handling requirements.

## Performance Considerations

Enabling OpenTelemetry instrumentation adds overhead to every request. The magnitude depends on your deployment's data volume, concurrency, and exporter configuration.

### Sources of overhead

- **Span creation** - The Django middleware creates a span for each HTTP request. Every instrumented Redis command and database query creates a child span. A single list-view request may produce 10-50 spans depending on the number of queries.
- **Database spans** - Each SQL query is wrapped in a span. Pages with many database queries (object detail views, bulk operations) produce the highest span volume. The SQL commenter feature also adds a small comment to every query.
- **Export** - The `BatchSpanProcessor` exports spans asynchronously in a background thread and does not block requests under normal conditions. If the OTLP endpoint is slow or unreachable, the processor's queue fills and back-pressure is applied to the request path.
- **Log correlation** - When `OTEL_PYTHON_LOG_CORRELATION` is `True`, trace and span IDs are injected into every log record, adding a small per-log overhead.

### Measuring impact

To establish a baseline before deploying to production, run a load test against a running Nautobot instance with and without `OTEL_PYTHON_DJANGO_INSTRUMENT=True`. Use a lightweight endpoint to isolate middleware overhead, and a data-heavy endpoint to measure instrumented library overhead:

```bash
# Lightweight - isolates middleware and context propagation cost
wrk -t4 -c50 -d30s http://localhost:8080/api/status/

# Data-heavy - exercises database and Redis span creation
wrk -t4 -c50 -d30s "http://localhost:8080/api/dcim/devices/?limit=50"
```

Compare p50, p95, and p99 latency across these configurations:

| Configuration | Notes |
| --- | --- |
| `OTEL_PYTHON_DJANGO_INSTRUMENT=False` | Baseline - no instrumentation |
| `OTEL_TRACES_EXPORTER=none` | Span creation cost only, no export |
| `OTEL_TRACES_EXPORTER=otlp` (local collector) | Typical production cost |
| `OTEL_TRACES_EXPORTER=console` | Worst case - synchronous stdout serialization |

Testing with `OTEL_TRACES_EXPORTER=none` isolates the cost of span creation and context propagation from export overhead, which helps identify whether any latency increase is due to instrumentation itself or the exporter.

### Reducing overhead

- Keep the OTLP collector on the same network as Nautobot. A slow or remote collector is the largest single risk to tail latency.
- Apply trace sampling at the collector (see [Trace sampling](#trace-sampling)) to reduce span volume without changing Nautobot's configuration.
- Under high concurrency, consider disabling metrics export (`OTEL_METRICS_EXPORTER=none`) and relying on sampling to reduce collector load.
- Avoid `OTEL_TRACES_EXPORTER=console` in production. It serializes each span synchronously to stdout and adds measurable overhead at volume.
- If database span volume is too high, tail-based sampling rules at the collector can exclude fast, successful database-only traces while retaining error traces and slow traces in full.
