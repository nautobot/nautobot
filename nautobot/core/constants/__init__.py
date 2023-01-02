SEARCH_MAX_RESULTS = 15

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


OBJ_TYPE_CHOICES = (
    ("", "All Objects"),
    (
        "Circuits",
        (
            ("provider", "Providers"),
            ("circuit", "Circuits"),
        ),
    ),
    (
        "DCIM",
        (
            ("site", "Sites"),
            ("rack", "Racks"),
            ("rackgroup", "Rack Groups"),
            ("devicetype", "Device types"),
            ("device", "Devices"),
            ("virtualchassis", "Virtual Chassis"),
            ("cable", "Cables"),
            ("powerfeed", "Power Feeds"),
        ),
    ),
    (
        "IPAM",
        (
            ("vrf", "VRFs"),
            ("aggregate", "Aggregates"),
            ("prefix", "Prefixes"),
            ("ipaddress", "IP addresses"),
            ("vlan", "VLANs"),
        ),
    ),
    ("Tenancy", (("tenant", "Tenants"),)),
    (
        "Virtualization",
        (
            ("cluster", "Clusters"),
            ("virtualmachine", "Virtual machines"),
        ),
    ),
)
