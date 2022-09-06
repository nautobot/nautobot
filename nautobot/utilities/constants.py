#
# Filter lookup expressions
#

FILTER_CHAR_BASED_LOOKUP_MAP = dict(
    n="exact",
    ic="icontains",
    nic="icontains",
    iew="iendswith",
    niew="iendswith",
    isw="istartswith",
    nisw="istartswith",
    ie="iexact",
    nie="iexact",
    re="regex",
    nre="regex",
    ire="iregex",
    nire="iregex",
)

FILTER_NUMERIC_BASED_LOOKUP_MAP = dict(n="exact", lte="lte", lt="lt", gte="gte", gt="gt")

FILTER_NEGATION_LOOKUP_MAP = dict(n="exact")

FILTER_TREENODE_NEGATION_LOOKUP_MAP = dict(n="in")

FILTER_LOOKUP_MAP = {
    "exact": "exact",
    "icontains": "contains",
    "iendswith": "ends-with",
    "istartswith": "starts-with",
    "iexact": "exact",
    "regex": "regex",
    "iregex": "regex",
    "lte": "less-than-or-equal",
    "lt": "less-than",
    "gte": "greater-than-or-equal",
    "gt": "greater-than",
    "in": "in",
}


#
# HTTP Request META safe copy
#

HTTP_REQUEST_META_SAFE_COPY = [
    "CONTENT_LENGTH",
    "CONTENT_TYPE",
    "HTTP_ACCEPT",
    "HTTP_ACCEPT_ENCODING",
    "HTTP_ACCEPT_LANGUAGE",
    "HTTP_HOST",
    "HTTP_REFERER",
    "HTTP_USER_AGENT",
    "QUERY_STRING",
    "REMOTE_ADDR",
    "REMOTE_HOST",
    "REMOTE_USER",
    "REQUEST_METHOD",
    "SERVER_NAME",
    "SERVER_PORT",
]
