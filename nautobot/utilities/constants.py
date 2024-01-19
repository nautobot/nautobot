from copy import deepcopy

import nh3

#
# Filter lookup expressions
#

FILTER_CHAR_BASED_LOOKUP_MAP = {
    "n": "exact",
    "ic": "icontains",
    "nic": "icontains",
    "iew": "iendswith",
    "niew": "iendswith",
    "isw": "istartswith",
    "nisw": "istartswith",
    "ie": "iexact",
    "nie": "iexact",
    "re": "regex",
    "nre": "regex",
    "ire": "iregex",
    "nire": "iregex",
}

FILTER_NUMERIC_BASED_LOOKUP_MAP = {
    "n": "exact",
    "lte": "lte",
    "lt": "lt",
    "gte": "gte",
    "gt": "gt",
}

FILTER_NEGATION_LOOKUP_MAP = {"n": "exact"}


#
# User input sanitization
#

# Subset of the HTML tags allowed by default by ammonia:
# https://github.com/rust-ammonia/ammonia/blob/master/src/lib.rs
HTML_ALLOWED_TAGS = nh3.ALLOWED_TAGS - {
    # no image maps at present
    "area",
    "map",
    # no document-level markup at present
    "article",
    "aside",
    "footer",
    "header",
    "nav",
    # miscellaneous out-of-scope for now
    "data",
    "dfn",
    "figcaption",
    "figure",
}

# Variant of the HTML attributes allowed by default by ammonia:
# https://github.com/rust-ammonia/ammonia/blob/master/src/lib.rs
# at present we just copy nh3.ALLOWED_ATTRIBUTES but we can modify this later as desired and appropriate
HTML_ALLOWED_ATTRIBUTES = deepcopy(nh3.ALLOWED_ATTRIBUTES)


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
