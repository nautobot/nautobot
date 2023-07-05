# Prometheus Metrics

+++ 1.5.13

It is possible for Nautobot apps to provide their own [Prometheus metrics](../../../user-guide/administration/guides/prometheus-metrics.md). There are two general ways to achieve this:

1. Use the `prometheus_client` library directly in your app code. Depending on whether that code runs in the web server or the worker context, the metric will show up in the respective `/metrics` endpoint(s) (i.e. metrics generated in the worker context show up in the worker's endpoint and those generated in the web application's context show up in the web application's endpoint).
2. If the metric cannot be generated alongside existing code, apps can implement individual metric generator functions and register them into a list called `metrics` in a file named `metrics.py` at the root of the app. Nautobot will automatically read these and expose them via its `/metrics` endpoint. The following code snippet shows an example metric defined this way:

```python
# metrics.py
from prometheus_client.metrics_core import GaugeMetricFamily

from nautobot_animal_sounds.models import Animal


def metric_animals():
    gauges = GaugeMetricFamily("nautobot_noisy_animals_count", "Nautobot Noisy Animals Count", labels=[])
    screaming_animal_count = Animal.objects.filter(loudness="noisy").count()
    gauges.add_metric(labels=[], value=screaming_animal_count)
    yield gauges


metrics = [metric_example]
```
