from copy import deepcopy

import nh3

LIVE_SEARCH_MAX_RESULTS = 10

SEARCH_MAX_RESULTS = 15

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

# For filters against JSON list values (multi-select custom fields), where negation must invert a `contains`
# lookup rather than an `exact` comparison against the whole list.
FILTER_CONTAINS_NEGATION_LOOKUP_MAP = {"n": "contains"}

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
    "approvalworkflow",
    "approvalworkflowdefinition",
    "approvalworkflowstage",
    "approvalworkflowstagedefinition",
    "approvalworkflowstageresponse",
    "cablepath",
    "cabletocabletermination",
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
    "deviceclusterassignment",
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
    "jobconsoleentry",
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

# M2M fields that are included by default in API responses if exclude_m2m is not provided
DEFAULT_M2M_FIELDS = ["tags", "content_types", "object_types"]

# Maximum number of homepage panels layout columns, for narrower device viewports columns will be wrapped.
HOMEPAGE_PANELS_LAYOUT_COLUMNS = 4

# Static branding assets per edition (edition -> branding key -> path). Every edition map is comprehensive,
# defining all branding keys; non-community editions reuse the community asset for any key they do not brand.
NAUTOBOT_STATIC_ASSETS = {
    "community": {
        "navbar_icon": "img/nautobot_icon.svg",
        "icon_16": "img/nautobot_icon_16x16.png",
        "icon_32": "img/nautobot_icon_32x32.png",
        "icon_180": "img/nautobot_icon_180x180.png",
        "icon_192": "img/nautobot_icon_192x192.png",
        "favicon": "img/favicon.ico",
        "icon_mask": "img/nautobot_icon_monochrome.svg",
        "logo": "img/nautobot_logo.svg",
    },
    "professional": {
        "navbar_icon": "img/professional/nautobot-professional-navbar-icon.svg",
        "icon_16": "img/professional/nautobot-professional-16x16.png",
        "icon_32": "img/professional/nautobot-professional-32x32.png",
        "icon_180": "img/professional/nautobot-professional-180x180.png",
        "icon_192": "img/professional/nautobot-professional-192x192.png",
        "favicon": "img/professional/nautobot-professional.ico",
        "icon_mask": "img/professional/nautobot-professional-monochrome.svg",
        "logo": "img/nautobot_logo.svg",
    },
    "enterprise": {
        "navbar_icon": "img/enterprise/nautobot-enterprise-navbar-icon.svg",
        "icon_16": "img/enterprise/nautobot-enterprise-16x16.png",
        "icon_32": "img/enterprise/nautobot-enterprise-32x32.png",
        "icon_180": "img/enterprise/nautobot-enterprise-180x180.png",
        "icon_192": "img/enterprise/nautobot-enterprise-192x192.png",
        "favicon": "img/enterprise/nautobot-enterprise.ico",
        "icon_mask": "img/enterprise/nautobot-enterprise-monochrome.svg",
        "logo": "img/nautobot_logo.svg",
    },
    "cloud": {
        "navbar_icon": "img/cloud/nautobot-cloud-navbar-icon.svg",
        "icon_16": "img/cloud/nautobot-cloud-16x16.png",
        "icon_32": "img/cloud/nautobot-cloud-32x32.png",
        "icon_180": "img/cloud/nautobot-cloud-180x180.png",
        "icon_192": "img/cloud/nautobot-cloud-192x192.png",
        "favicon": "img/cloud/nautobot-cloud.ico",
        "icon_mask": "img/cloud/nautobot-cloud-monochrome.svg",
        "logo": "img/nautobot_logo.svg",
    },
}

# Per-edition product page URLs.
NAUTOBOT_EDITION_URLS = {
    "community": "https://networktocode.com/nautobot",
    "professional": "https://networktocode.com/nautobot/nautobot-professional/",
    "enterprise": "https://networktocode.com/nautobot/nautobot-enterprise/",
    "cloud": "https://networktocode.com/nautobot/nautobot-cloud/",
}

#
# Settings allowed to be retrieved from templates
#

# Allowlist of Django settings and Constance configuration keys that are safe to read from a rendered
# template. This gates what the `settings_or_config` template filter and the template `settings` context
# may return (see `nautobot.core.utils.config.is_template_exposable_setting`).
TEMPLATE_EXPOSED_SETTINGS = frozenset(
    {
        "ALLOW_REQUEST_PROFILING",
        "BANNER_BOTTOM",
        "BANNER_LOGIN",
        "BANNER_TOP",
        "BRANDING_FILEPATHS",
        "BRANDING_POWERED_BY_URL",
        "BRANDING_TITLE",
        "BRANDING_URLS",
        "CELERY_TASK_SOFT_TIME_LIMIT",
        "CELERY_TASK_TIME_LIMIT",
        "CHANGELOG_RETENTION",
        "CONFIG_CONTEXT_DYNAMIC_GROUPS_ENABLED",
        "DATE_FORMAT",
        "DATETIME_FORMAT",
        "DEPLOYMENT_ID",
        "DEVICE_UNIQUENESS",
        "HOSTNAME",
        "JOB_CREATE_FILE_MAX_SIZE",
        "LOCATION_LIST_DEFAULT_MAX_DEPTH",
        "LOCATION_NAME_AS_NATURAL_KEY",
        "LOGIN_URL",
        "MAINTENANCE_MODE",
        "MAX_PAGE_SIZE",
        "MEDIA_ROOT",
        "NETWORK_DRIVERS",
        "NTC_SUPPORT_CONTRACT_EXPIRATION_DATE",
        "PAGINATE_COUNT",
        "PER_PAGE_DEFAULTS",
        "PREFER_IPV4",
        "PREFIX_LIST_DEFAULT_CONTAINER_ONLY",
        "PREFIX_LIST_DEFAULT_MAX_DEPTH",
        "PUBLISH_ROBOTS_TXT",
        "RACK_DEFAULT_U_HEIGHT",
        "RACK_ELEVATION_DEFAULT_UNIT_HEIGHT",
        "RACK_ELEVATION_DEFAULT_UNIT_WIDTH",
        "RACK_ELEVATION_UNIT_TWO_DIGIT_FORMAT",
        "REDIS_LOCK_TIMEOUT",
        "RELEASE_CHECK_TIMEOUT",
        "RELEASE_CHECK_URL",
        "SETTINGS_PATH",
        "SHORT_DATE_FORMAT",
        "SHORT_DATETIME_FORMAT",
        "STATIC_ROOT",
        "STATIC_URL",
        "SUPPORT_MESSAGE",
        "TIME_FORMAT",
        "URL_FORMAT_OVERRIDE",
        "VERSION",
    }
)
