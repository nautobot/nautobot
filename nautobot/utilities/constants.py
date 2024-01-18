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
HTML_ALLOWED_TAGS = {
    "a",
    "abbr",
    "acronym",
    "b",
    "blockquote",
    "br",
    "code",
    "dd",
    "del",
    "div",
    "dl",
    "dt",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "img",
    "ins",
    "kbd",
    "li",
    "ol",
    "p",
    "pre",
    "span",
    "strike",
    "strong",
    "sub",
    "sup",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "tt",
    "u",
    "ul",
    "var",
}

# Subset of the HTML attributes allowed by default by ammonia:
# https://github.com/rust-ammonia/ammonia/blob/master/src/lib.rs
HTML_ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "hr": {"align", "size", "width"},
    "img": {"align", "alt", "height", "src", "title", "width"},
    "ol": {"start"},
    "tbody": {"align"},
    "td": {"align", "colspan", "rowspan"},
    "th": {"align", "colspan", "rowspan"},
    "thead": {"align"},
    "tr": {"align"},
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
