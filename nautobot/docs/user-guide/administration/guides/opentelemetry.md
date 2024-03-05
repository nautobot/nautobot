# OpenTelemetry

+++ 2.2.0

Nautobot supports optionally exposing logs, traces, and metrics via [OpenTelemetry](https://opentelemetry.io/).

## Install

See the [Install Guide](../configuration/opentelemetry.md) for installation instructions.

## Configuration

OpenTelemetry logs, traces, and metrics are not exposed by default. To enable this, the `OTEL_PYTHON_DJANGO_INSTRUMENT` setting should be set to `True`. This will do two things:

- Logs will be exposed in the OpenTelemetry format and include the Trace ID, Span ID, and Resource attributes.
- Metrics and Traces will be logged to console.

### Logs

When enabling OpenTelemetry, the logs sent to stdout will have additional information added.

Without OpenTelemetry enabled, logs look like:

```bash
nautobot-nautobot-1       | 04:11:42.768 INFO    django.server :
nautobot-nautobot-1       |   "GET /health/ HTTP/1.1" 200 11469
```

**With** OpenTelemetry enabled, logs look like:

```bash

```

### Exporting traces and metrics via OTLP

In order to export the traces and metrics via OTLP (OpenTelemetry Protocol), the `OTEL_TRACES_EXPORTER` and `OTEL_METRICS_EXPORTER` should be set to `otlp`.

Once those are set, you need to specify the OTLP endpoint via the `OTEL_EXPORTER_OTLP_ENDPOINT` setting. If necessary, you can set the OTLP protocol via `OTEL_EXPORTER_OTLP_PROTOCOL` to either `grpc` (default) or `http`. If setting to `grpc`, you can also send the metrics insecurely by setting `OTEL_EXPORTER_OTLP_INSECURE` to `True`.

## Receiving OTLP Data

The OTLP collector is outside of the Nautobot scope. Common open source collectors include the [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/) and [Grafana Agent](https://grafana.com/docs/agent/latest/).

### Sample Tracing and Metric Pipeline Configuration

The Nautobot development folder has a sample configuration of using the OpenTelemetry Collector that forwards to [Grafana Tempo](https://grafana.com/oss/tempo/) and [Grafana Mimir](https://grafana.com/oss/mimir/).

The `docker-compose.observability.yml` file has all of the items necessary to start observing logs, traces, and metrics. All of the necessary config files for Grafana, Mimir, OTEL, Promtail, and Tempo are included as well.
