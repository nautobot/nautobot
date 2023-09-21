SEARCH_MAX_RESULTS = 15

#
# Filter lookup expressions
#

SEARCH_MAX_RESULTS = 15

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
# Reserved Names
#

RESERVED_NAMES_FOR_OBJECT_DETAIL_VIEW_SCHEMA = ["Other Fields", "Object Details"]

#
# Factory defaults
#

NAUTOBOT_BOOL_ITERATOR_DEFAULT_LENGTH = 8
NAUTOBOT_BOOL_ITERATOR_DEFAULT_PROBABILITY = 50


#
# CSV Import/Export
#

CSV_NON_TYPE = "NULL"
CSV_OBJECT_NOT_FOUND = "ObjectNotFound"
# VarbinaryIPField Represents b'ObjectNotFound' as `0:4f62:6a65:6374:4e6f:7446:6f75:6e64`
VARBINARY_IP_FIELD_REPR_OF_OBJECT_NOT_FOUND = "0:4f62:6a65:6374:4e6f:7446:6f75:6e64"


# For our purposes, COMPOSITE_KEY_SEPARATOR needs to be:
# 1. Safe in a URL path component (so that we can do URLS like "/dcim/devices/<composite_key>/delete/")
#    Per RFC3986 section 2.3 the general "unreserved" characters are ALPHA and DIGIT and the characters -._~
#    Per RFC3986 section 3.3 path components also permit characters :@ and the "sub-delims" characters !$&'()*+,;=
# 2. Not readily confused with characters commonly seen in un-escaped natural key component fields
#    "." is already ruled out as an unreserved character but also would appear in IPv4 IPAddress and Prefix objects
#    ":" similarly would appear in IPv6 IPAddress/Prefix objects
#    "/" would appear in Prefix objects as well as various numbered device component names
# 3. Safe in a URL query string component (so that we can do URLs like "/dcim/devices/?location=<composite_key>"
#    This rules out "&" and "="
COMPOSITE_KEY_SEPARATOR = ";"

# For the natural slug separator, it's much simpler and we can just go with "_".
NATURAL_SLUG_SEPARATOR = "_"
