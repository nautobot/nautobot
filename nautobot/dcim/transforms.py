"""Transforms for DCIM app."""

from django.db.models import CharField, Transform


class IPString(Transform):  # pylint: disable=abstract-method
    """Transform to convert bytea IP address to string representation."""

    lookup_name = "ipstr"
    output_field = CharField()
    function = "bytea_to_ip_string"
