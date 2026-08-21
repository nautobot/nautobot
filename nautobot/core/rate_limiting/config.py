from django.conf import settings

MODE_OFF = "off"
MODE_REPORT = "report"
MODE_ENFORCE = "enforce"

VALID_MODES = frozenset({MODE_OFF, MODE_REPORT, MODE_ENFORCE})

KIND_REST = "rest"
KIND_GRAPHQL = "graphql"
RATE_LIMITING_DEFAULTS = {
    # "off" | "report" | "enforce", applying to all request kinds; or a per-kind mapping such as
    # {"rest": "enforce", "graphql": "report"}, with unmapped kinds treated as "off".
    "MODE": MODE_OFF,
    # Length of each token's budget window. The window is anchored to the token's first request
    # (the Redis key's TTL); expiry is the reset.
    "WINDOW_SECONDS": 60,
    # Budget per token per window, in cost points. Enforcement denies once *already-recorded*
    # recorded consumption reaches this value.
    # TODO: Overloaded term with DRF, suggest name chang    e
    "LIMIT": 1000,
    # Overrides merged over the shipped heuristic weight defaults; see the *_DEFAULT_WEIGHTS
    # dicts in nautobot.core.rate_limiting (rest_cost, graphql_cost, costing) for the available
    # keys, and costing.FLAT_WEIGHTS for the flat requests-per-window preset.
    # TODO: Remove?
    "HEURISTIC_WEIGHTS": {},
    # When True, emit one structured JSON record per request to the
    # "nautobot.core.rate_limiting.calibration" logger, pairing the assigned cost with measured
    # wall-clock/CPU/database time so the heuristic weights can be regressed offline.
    "CALIBRATION_LOG": False,
    # Per-request sampling probability (0.0-1.0) for the calibration log.
    "CALIBRATION_SAMPLE_RATE": 1.0,
}

def get_rate_limiting_configuration():
    """Return the effective NAUTOBOT_RATE_LIMITING_SETTINGS configuration (shipped defaults merged under operator overrides)."""
    rate_limit_configurations = {
        **RATE_LIMITING_DEFAULTS,
        # TODO: Make sure this exposes the rate limiting values via environment
        #       variables in order to allow overrides without code update
        **getattr(settings, "NAUTOBOT_RATE_LIMITING_SETTINGS", {})
    }

    return rate_limit_configurations