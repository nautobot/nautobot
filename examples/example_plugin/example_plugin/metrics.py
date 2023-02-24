from prometheus_client.metrics_core import GaugeMetricFamily


def metric_example():
    from example_plugin.models import ExampleModel

    gauges = GaugeMetricFamily("nautobot_example_metric_count", "Nautobot Example Count Metric", labels=["name"])

    # This is very slow on larger tables. Shouldn't matter for the example plugin.
    example_model_instance = ExampleModel.objects.order_by("?").first()

    gauges.add_metric(labels=[example_model_instance.name], value=example_model_instance.number)
    yield gauges


metrics = [metric_example]
