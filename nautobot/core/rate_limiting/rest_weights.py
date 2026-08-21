from django.conf import settings

REST_DEFAULT_WEIGHTS = {
    "read_cost": 1.0,
    "write_cost": 3.0,
    "records_per_page_divisor": 50,
    "per_join_cost": 1.0,
    "unindexable_lookup_cost": 5.0,
    "depth_multiplier_per_level": 1.0,
    "computed_fields_multiplier": 3.0,
    "csv_multiplier": 3.0,
    **getattr(settings, "NAUTOBOT_REST_RATE_LIMITING_DEFAULT_SETTINGS", {})
}
