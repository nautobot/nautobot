# Keys/values for the metadata format shared by CSV/JSON/YAML import and export. In JSON/YAML these are
# document keys; in CSV the version appears as the leading `# key=value` directive, which is also what
# identifies the row as Nautobot's (there is no separate marker).
# The version continues Nautobot's existing lineage: 1 was Nautobot 1.x and 2 was 2.x through 3.2, neither of
# which declared a version, so a file with no version key is either version 1 or 2.
IMPORT_DOCUMENT_VERSION = 3
IMPORT_DOCUMENT_VERSION_KEY = "nautobot_import_version"
IMPORT_DOCUMENT_MODEL_KEY = "model"
IMPORT_DOCUMENT_MATCH_FIELDS_KEY = "match_fields"
IMPORT_DOCUMENT_RECORDS_KEY = "records"

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
