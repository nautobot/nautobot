from copy import deepcopy

import nh3

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

CSV_NULL_TYPE = "NULL"
CSV_NO_OBJECT = "NoObject"
# VarbinaryIPField Represents b'NoObject' as `::4e6f:4f62:6a65:6374`
VARBINARY_IP_FIELD_REPR_OF_CSV_NO_OBJECT = "::4e6f:4f62:6a65:6374"


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

# For config settings that contain a list of things.
# As environment variables only allow string types, these need to be split into the final list.
CONFIG_SETTING_SEPARATOR = ","

CHARFIELD_MAX_LENGTH = 255

# Default values for pagination settings.
MAX_PAGE_SIZE_DEFAULT = 1000
PAGINATE_COUNT_DEFAULT = 50

# Models excluded from the global search list
GLOBAL_SEARCH_EXCLUDE_LIST = [
    "anotherexamplemodel",
    "cablepath",
    "circuittermination",
    "circuittype",
    "clustergroup",
    "clustertype",
    "computedfield",
    "configcontext",
    "configcontextschema",
    "consoleport",
    "consoleporttemplate",
    "consoleserverport",
    "consoleserverporttemplate",
    "contactassociation",
    "controllermanageddevicegroup",
    "customfield",
    "customfieldchoice",
    "customlink",
    "devicebay",
    "devicebaytemplate",
    "devicetypetosoftwareimagefile",
    "dynamicgroupmembership",
    "exporttemplate",
    "fileattachment",
    "fileproxy",
    "frontport",
    "frontporttemplate",
    "graphqlquery",
    "healthchecktestmodel",
    "imageattachment",
    "interface",
    "interfaceredundancygroup",
    "interfaceredundancygroupassociation",
    "interfacetemplate",
    "interfacevdcassignment",
    "inventoryitem",
    "ipaddresstointerface",
    "job",
    "jobbutton",
    "jobhook",
    "joblogentry",
    "jobqueue",
    "jobqueueassignment",
    "jobresult",
    "locationtype",
    "manufacturer",
    "metadatachoice",
    "metadatatype",
    "modulebay",
    "modulebaytemplate",
    "note",
    "objectchange",
    "objectmetadata",
    "platform",
    "poweroutlet",
    "poweroutlettemplate",
    "powerpanel",
    "powerport",
    "powerporttemplate",
    "prefixlocationassignment",
    "rackreservation",
    "rearport",
    "rearporttemplate",
    "relationship",
    "relationshipassociation",
    "rir",
    "role",
    "routetarget",
    "savedview",
    "scheduledjob",
    "scheduledjobs",
    "secret",
    "secretsgroup",
    "secretsgroupassociation",
    "service",
    "softwareimagefile",
    "staticgroupassociation",
    "status",
    "tag",
    "taggeditem",
    "tenantgroup",
    "usersavedviewassociation",
    "vlangroup",
    "vlanlocationassignment",
    "vminterface",
    "vrfdeviceassignment",
    "vrfprefixassignment",
    "webhook",
]
