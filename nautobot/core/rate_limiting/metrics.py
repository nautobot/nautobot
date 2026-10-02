from prometheus_client import Counter, Histogram

MILLISECONDS_PER_SECOND = 1_000
COMPLEXITY_COST_BUCKETS = (1, 2, 5, 10, 25, 50, 100, 250, 500, 1_000)

# ------------------------------------------------------------------------------
# Server-Timing - Total Duration
# ------------------------------------------------------------------------------
# TODO: Revisit this when tokens store username and add to labels
rest_request_total_duration_in_seconds_histogram = Histogram(
    name="nautobot_rest_request_total_duration_in_seconds",
    documentation="Total wall clock duration of requests",
    labelnames=("hashed_token",),
    buckets=COMPLEXITY_COST_BUCKETS,
)


def record_rest_request_total_duration(hashed_token, request_total_duration_in_milliseconds):
    duration_in_seconds = request_total_duration_in_milliseconds / MILLISECONDS_PER_SECOND
    rest_request_total_duration_in_seconds_histogram.labels(hashed_token).observe(duration_in_seconds)


# ------------------------------------------------------------------------------
# Server-Timing - DB Duration
# ------------------------------------------------------------------------------
# TODO: Revisit this when tokens store username and add to labels
rest_request_db_duration_in_seconds_histogram = Histogram(
    name="nautobot_rest_request_db_duration_in_seconds",
    documentation="Total time executing database queries during requests",
    labelnames=("hashed_token",),
    buckets=COMPLEXITY_COST_BUCKETS,
)


def record_rest_request_db_duration(hashed_token, request_db_duration_in_milliseconds):
    duration_in_seconds = request_db_duration_in_milliseconds / MILLISECONDS_PER_SECOND
    rest_request_db_duration_in_seconds_histogram.labels(hashed_token).observe(duration_in_seconds)


# ------------------------------------------------------------------------------
# Nautobot Cost
# ------------------------------------------------------------------------------
# TODO: Revisit this when tokens store username and add to labels
rest_request_complexity_cost_counter = Counter(
    name="nautobot_rest_request_complexity_cost",
    documentation="The cumulative cost of every complexity cost charge for rate limiting.",
    labelnames=("hashed_token",),
)


def record_rest_request_complexity_cost(hashed_token, current_charge):
    rest_request_complexity_cost_counter.labels(hashed_token).inc(current_charge)


# TODO: Revisit this when tokens store username and add to labels
rest_rate_limiting_backend_errors_counter = Counter(
    name="nautobot_rest_rate_limiting_backend_errors",
    documentation="Budget charge attempts that could not be completed against the Redis backend",
    labelnames=("hashed_token", "exception_type", "exception"),
)


def record_rest_request_rate_limiting_backend_exception(hashed_token, exception):
    exception_type = type(exception).__name__
    rest_rate_limiting_backend_errors_counter.labels(
        hashed_token,
        exception_type,
        str(exception),
    ).inc()
