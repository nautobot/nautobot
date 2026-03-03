# OpenTelemetry

+++ 3.2.0

Nautobot supports optionally exposing logs, traces, and metrics via [OpenTelemetry](https://opentelemetry.io/).

## Install

See the [Install Guide](../configuration/opentelemetry.md) for installation instructions.

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

## Performance Considerations

Enabling OpenTelemetry instrumentation adds overhead to every request. The magnitude depends on your deployment's data volume, concurrency, and exporter configuration.

### Sources of overhead

- **Span creation** - The Django middleware creates a span for each HTTP request. Every instrumented Redis command and database query creates a child span. A single list-view request may produce 10-50 spans depending on the number of queries.
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
- Under high concurrency, consider disabling metrics export (`OTEL_METRICS_EXPORTER=none`) and relying on sampling configured at the collector to reduce span volume.
- Avoid `OTEL_TRACES_EXPORTER=console` in production. It serializes each span synchronously to stdout and adds measurable overhead at volume.
