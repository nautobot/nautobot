import dataclasses
import math

from nautobot.core.rate_limiting.config import KIND_REST
from nautobot.core.utils.data import to_int_or_none

# logger = logging.getLogger(__name__)

# Query params that are pagination/rendering controls, not filters.
NON_FILTER_PARAMS = frozenset(
    {
        "limit",  # pagination: max items per page
        "offset",  # pagination: window start index
        "depth",  # serializer nesting; priced separately
        "format",  # renderer: json | api | csv; priced separately
        "include",  # opt-in fields; priced separately
        "exclude",  # NOTE: real param is `exclude_m2m`
        "sort",  # result ordering
        "api_version",  # REST API version selector
        "brief",  # Nautobot 1.x; removed in 2.0
        "q",  # NOTE: really a SearchFilter (icontains) — unpriced here
    }
)


# TODO: I don't like these lookup specifications but don't have enough information
#       to correctly articulate why
UNINDEXABLE_LOOKUPS = frozenset(
    {
        # Django-style — leading wildcard or regex
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
        "nie",  # (not) iexact — inconsistent with "iexact" below
        "iew",  # iendswith
        "niew",  # (not) iendswith
        "re",  # regex
        "nre",  # (not) regex
        "ire",  # iregex
        "nire",  # (not) iregex
    }
)

# Lookups that are index-friendly
# Listed so they aren't miscounted as relation traversals
INDEXABLE_LOOKUPS = frozenset(
    {
        "n",  # negated exact
        "exact",  # col = val
        "iexact",  # UPPER(col) = UPPER(val) — needs functional index
        "in",  # col IN (...)
        "gt",  # col > val
        "gte",  # col >= val
        "lt",  # col < val
        "lte",  # col <= val
        "isnull",  # col IS NULL
        "startswith",  # LIKE 'val%' — needs varchar_pattern_ops
        "istartswith",  # UPPER(col) LIKE UPPER('val%') — needs functional index
        "isw",  # short form of istartswith
        "nisw",  # (not) istartswith
    }
)

READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


@dataclasses.dataclass
class RestRequestFeatures:
    request_method: str
    records_per_page: int | None = None  # AKA Limit parameter
    depth: int = 0
    opt_in_fields: list[str] = dataclasses.field(default_factory=list)
    response_format: str = ""
    filter_count: int = 0
    join_traversals: int = 0
    unindexable_lookups: int = 0
    lookups: list[str] = dataclasses.field(default_factory=list)  # e.g. ["name__ic", "location__name"]
    # When set, cost computation failed and the counting fields above were never populated.
    classification_error: bool = False
    kind: str = KIND_REST

    def is_response_format_csv(self):
        return self.response_format == "csv"

    def do_computed_fields_exist(self):
        return "computed_fields" in self.opt_in_fields


def classify_rest_request_features(request, weights):
    """Generate a RestRequestFeatures object that indicates specific features
    of a REST request
    """
    # TODO: Add tests for `POST/PUT` (DELETE?)?
    query_parameters = request.GET

    # TODO: Revisit for upper bounds
    depth_query_parameter = to_int_or_none(query_parameters.get("depth")) or 0
    maximized_depth = max(depth_query_parameter, 0)
    clamped_depth = min(maximized_depth, 1000)  # hard-code, but pull from settings later

    # TODO: Revisit this so that it accounts for min/max boundary conditions
    records_per_page_parameter = to_int_or_none(query_parameters.get("limit"))

    rest_request_features = RestRequestFeatures(
        request_method=request.method,
        records_per_page=records_per_page_parameter,
        depth=clamped_depth,
        opt_in_fields=query_parameters.getlist("include"),
        response_format=query_parameters.get("format"),
    )

    for raw_key in query_parameters.keys():
        key = raw_key.strip()

        if key in NON_FILTER_PARAMS or not key:
            continue

        rest_request_features.filter_count += 1
        segments = key.split("__")

        # Remove
        last_segment = segments[-1]
        if last_segment in UNINDEXABLE_LOOKUPS:
            rest_request_features.unindexable_lookups += 1
            segments = segments[:-1]
        elif last_segment in INDEXABLE_LOOKUPS:
            segments = segments[:-1]

        # TODO: Discuss this
        # I don't know that I agree with this property? `join_traversals`
        # implies that there is a join operation performed
        # In the case of this url
        # /api/dcim/devices/?limit=1000&depth=3&name__ic=foo
        # <QueryDict: {'limit': ['1000'], 'depth': ['3'], 'name__ic': ['foo']}>
        # By the time it hits this section the `ic` piece is stripped and
        # and the `name` remains, and this is still a proprty of the device object
        # The name__ic isn't a relational field, meaning a join isn't required
        rest_request_features.join_traversals += max(len(segments) - 1, 0)
        rest_request_features.lookups.append(key)

    return rest_request_features


def estimate_rest_request_cost(rest_request_features, weights):
    """Using a RestRequestFeatures object, provide an estimate for what the cost"""

    # Assume default operation is read, otherwise change to write
    rest_action_cost = weights["read_cost"]
    if rest_request_features.request_method not in READ_METHODS:
        rest_action_cost = weights["write_cost"]

    total_request_cost = 0

    total_request_cost += float(rest_action_cost)

    per_join_cost = rest_request_features.join_traversals * weights["per_join_cost"]
    total_request_cost += per_join_cost

    unindexable_lookups_cost = rest_request_features.unindexable_lookups * weights["unindexable_lookup_cost"]
    total_request_cost += unindexable_lookups_cost

    if rest_request_features.records_per_page:
        page_count = math.ceil(rest_request_features.records_per_page / weights["records_per_page_divisor"])
        total_request_cost *= max(page_count, 1)

    if rest_request_features.depth != 0:
        # TODO: I still don't understand nautobot depth
        #       Also not sure why it's 1 if depth is zero, shouldn't this be a
        #       zero cost?
        depth_cost = 1 + rest_request_features.depth * weights["depth_multiplier_per_level"]
        total_request_cost *= depth_cost

    if rest_request_features.do_computed_fields_exist():
        computed_fields_cost = weights["computed_fields_multiplier"]
        total_request_cost *= computed_fields_cost

    if rest_request_features.is_response_format_csv():
        csv_cost = weights["csv_multiplier"]
        total_request_cost *= csv_cost

    rounded_total_request_cost = round(total_request_cost, 2)
    return rounded_total_request_cost
