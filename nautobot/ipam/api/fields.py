import netaddr
from rest_framework import serializers


class IPFieldSerializer(serializers.CharField):
    def to_representation(self, value):
        """Convert internal (IPNetwork) representation to API (string) representation."""
        return str(value)

    def to_internal_value(self, data):
        """Convert API (string) representation to internal (IPNetwork) representation."""
        try:
            return netaddr.IPNetwork(data)
        except netaddr.AddrFormatError:
            raise serializers.ValidationError(f"Invalid IP address format: {data}")
        except (TypeError, ValueError) as e:
            raise serializers.ValidationError(e)


class IPAddressFieldSerializer(serializers.CharField):
    """Serializer field for a bare host address (no mask), backed by netaddr.IPAddress."""

    def to_representation(self, value):
        """Convert internal (IPAddress) representation to API (string) representation."""
        return str(value) if value is not None else None

    def to_internal_value(self, data):
        """Convert API (string) representation to internal (IPAddress) representation."""
        try:
            return netaddr.IPAddress(data)
        except netaddr.AddrFormatError:
            raise serializers.ValidationError(f"Invalid IP address format: {data}")
        except (TypeError, ValueError) as e:
            raise serializers.ValidationError(str(e))
