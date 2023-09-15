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
