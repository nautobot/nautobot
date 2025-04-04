from prometheus_client.metrics_core import GaugeMetricFamily

from example_app.models import ExampleModel


def metric_example():
    gauges = GaugeMetricFamily("nautobot_example_metric_count", "Nautobot Example Count Metric", labels=["name"])

    # This is very slow on larger tables. Shouldn't matter for the example App.
    example_model_instance = ExampleModel.objects.order_by("?").first()

    if example_model_instance:
        gauges.add_metric(labels=[example_model_instance.name], value=example_model_instance.number)
    else:
        # If no model instance is there, provide an empty metric.
        gauges.add_metric(labels=[], value=0)
    yield gauges


metrics = [metric_example]
