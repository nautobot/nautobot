from prometheus_client import Counter, Histogram

from nautobot.core.utils.requests import get_view_name_for_request

COMPLEXITY_COST_BUCKETS = (1, 2, 5, 10, 25, 50, 100, 250, 500, 1_000)

rest_request_complexity_cost_metric = Histogram(
    name="nautobot_rest_request_complexity_cost",
    documentation="Estimated complexity cost of REST API requests",
    labelnames=("method", "endpoint", "rate_limiting_mode", "outcome"),
    buckets=COMPLEXITY_COST_BUCKETS,
)

rest_rate_limiting_backend_errors_counter = Counter(
    name="nautobot_rest_rate_limiting_backend_errors",
    documentation="Budget charge attempts that could not be completed against the Redis backend",
    labelnames=("method", "endpoint", "rate_limiting_mode", "exception_type"),
)


def record_rest_request_complexity_cost(request, rate_limiting_mode, outcome, complexity_cost):
    endpoint_name = get_view_name_for_request(request)
    rest_request_complexity_cost_metric.labels(
        request.method,
        endpoint_name,
        rate_limiting_mode,
        outcome,
    ).observe(complexity_cost)


def record_rest_rate_limiting_backend_exception(request, rate_limiting_mode, exception):
    endpoint_name = get_view_name_for_request(request)
    exception_type_name = type(exception).__name__
    rest_rate_limiting_backend_errors_counter.labels(
        request.method,
        endpoint_name,
        rate_limiting_mode,
        exception_type_name,
    ).inc()


# TO DO: Add Server-Timing to this
