# Query parameters that are *not* filterset filters
NON_FILTER_QUERY_PARAMS = (
    "api_version",  # used to select the Nautobot API version
    "depth",  # nested levels of the serializers default to depth=0
    "exclude_m2m",  # used to exclude many-to-many fields from the REST API
    "format",  # "json" or "api", used in the interactive HTML REST API views
    "include",  # used to include computed fields, relationships, config-contexts, etc. (excluded by default)
    "limit",  # pagination
    "offset",  # pagination
    "sort",  # sorting of results
)
