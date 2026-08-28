import dataclasses
import math

from django.conf import settings

from nautobot.core.constants import MAX_PAGE_SIZE_DEFAULT, PAGINATE_COUNT_DEFAULT
from nautobot.core.utils.config import get_settings_or_config
from nautobot.core.utils.data import to_int_or_none

# Query params that are pagination/rendering controls, not filters.
NON_FILTER_PARAMS = frozenset(
    {
        "limit",  # pagination: records per page
        "offset",  # pagination: current page
        "depth",  # serializer nesting
        "format",  # renderer: json | api | csv
        "include",  # opt-in fields
        "exclude",
        "sort",  # result ordering
        "api_version",  # REST API version selector
        "q",  # NOTE: really a SearchFilter (icontains) — unpriced here
    }
)

UNINDEXABLE_LOOKUPS = frozenset(
    {
        # Django Lookups
        "icontains",  # ILIKE '%val%'
        "contains",  # LIKE '%val%'
        "iregex",  # ~* 'val'
        "regex",  # ~ 'val'
        "iendswith",  # ILIKE '%val'
        "endswith",  # LIKE '%val'
        # Nautobot short forms
        "ic",  # icontains
        "nic",  # (not) icontains
        "ie",  # iexact
        "nie",  # (not) iexact
        "iew",  # iendswith
        "niew",  # (not) iendswith
        "re",  # regex
        "nre",  # (not) regex
        "ire",  # iregex
        "nire",  # (not) iregex
    }
)

INDEXABLE_LOOKUPS = frozenset(
    {
        # Django Lookups
        "n",  # negated exact
        "exact",  # col = val
        "iexact",  # UPPER(col) = UPPER(val)
        "in",  # col IN (...)
        "gt",  # col > val
        "gte",  # col >= val
        "lt",  # col < val
        "lte",  # col <= val
        "isnull",  # col IS NULL
        "startswith",  # LIKE 'val%'
        "istartswith",  # UPPER(col) LIKE UPPER('val%')
        # Nautobot short forms
        "isw",  # short form of istartswith
        "nisw",  # (not) istartswith
    }
)

READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def calculate_records_per_page(requested_records_per_page):
    """Resolve how many records will be returned for this request."""
    max_page_size = get_settings_or_config("MAX_PAGE_SIZE", fallback=MAX_PAGE_SIZE_DEFAULT)
    default_records_per_page = get_settings_or_config("PAGINATE_COUNT", fallback=PAGINATE_COUNT_DEFAULT)

    # Absent, non-numeric, and negative values all fall back to the server default
    if requested_records_per_page is None or requested_records_per_page < 0:
        return default_records_per_page
    # With the cap disabled, `limit=0` serves every record, so the page size is unbounded
    if not max_page_size:
        return math.inf if requested_records_per_page == 0 else requested_records_per_page
    if requested_records_per_page == 0:
        return max_page_size
    return min(requested_records_per_page, max_page_size)


@dataclasses.dataclass
class RestReadRequestFeatures:
    records_per_page: int | None = None  # AKA Limit parameter
    depth: int = 0
    opt_in_fields: list[str] = dataclasses.field(default_factory=list)
    response_format: str = ""
    filter_count: int = 0
    indexable_lookups: int = 0
    unindexable_lookups: int = 0

    def is_response_format_csv(self):
        return self.response_format == "csv"

    def do_computed_fields_exist(self):
        return "computed_fields" in self.opt_in_fields


def classify_rest_read_request_features(request):
    """Take a `request` object and returns a `RestReadRequestFeatures` object"""
    query_parameters = request.GET

    # TODO: Revisit for upper bounds
    depth_query_parameter = to_int_or_none(query_parameters.get("depth")) or 0
    maximized_depth = max(depth_query_parameter, 0)
    clamped_depth = min(maximized_depth, 1000)  # hard-code, but pull from settings later

    # TODO: Revisit this so that it accounts for min/max boundary conditions
    records_per_page_parameter = to_int_or_none(query_parameters.get("limit"))

    rest_read_request_features = RestReadRequestFeatures(
        records_per_page=records_per_page_parameter,
        depth=clamped_depth,
        opt_in_fields=query_parameters.getlist("include"),
        response_format=query_parameters.get("format"),
    )

    for raw_key in query_parameters.keys():
        key = raw_key.strip()

        if key in NON_FILTER_PARAMS or not key:
            continue

        rest_read_request_features.filter_count += 1
        # name__ic -> ["name", "ic"]
        segments = key.split("__")

        last_segment = segments[-1]
        if last_segment in INDEXABLE_LOOKUPS:
            rest_read_request_features.indexable_lookups += 1
        if last_segment in UNINDEXABLE_LOOKUPS:
            rest_read_request_features.unindexable_lookups += 1

    return rest_read_request_features


def estimate_rest_read_request_cost(rest_read_request_features):
    """Using a RestReadRequestFeatures object, provide an estimate for what the cost"""

    total_request_cost = 0

    total_request_cost += settings.NAUTOBOT_REST_RATE_LIMITING_READ_COST

    # TODO: discuss this numerator anchoring
    placeholder_record_count = 20
    nautobot_allowed_records_per_page = calculate_records_per_page(rest_read_request_features.records_per_page)
    # Floored at one: no result set, however small, is retrievable in fewer than one request
    pages_required_for_full_read = max(1, math.ceil(placeholder_record_count / nautobot_allowed_records_per_page))
    pagination_cost = pages_required_for_full_read * settings.NAUTOBOT_REST_RATE_LIMITING_PAGINATION_COST
    total_request_cost += pagination_cost

    if rest_read_request_features.depth != 0:
        depth_cost = (
            1 + rest_read_request_features.depth * settings.NAUTOBOT_REST_RATE_LIMITING_DEPTH_MULTIPLIER_PER_LEVEL
        )
        total_request_cost *= depth_cost

    indexable_lookups_cost = (
        rest_read_request_features.indexable_lookups * settings.NAUTOBOT_REST_RATE_LIMITING_INDEXABLE_LOOKUP_COST
    )
    total_request_cost += indexable_lookups_cost

    unindexable_lookups_cost = (
        rest_read_request_features.unindexable_lookups * settings.NAUTOBOT_REST_RATE_LIMITING_UNINDEXABLE_LOOKUP_COST
    )
    total_request_cost += unindexable_lookups_cost

    if rest_read_request_features.do_computed_fields_exist():
        total_request_cost *= settings.NAUTOBOT_REST_RATE_LIMITING_COMPUTED_FIELDS_MULTIPLIER

    if rest_read_request_features.is_response_format_csv():
        total_request_cost *= settings.NAUTOBOT_REST_RATE_LIMITING_CSV_MULTIPLIER

    rounded_total_request_cost = round(total_request_cost, 2)

    return rounded_total_request_cost
