from collections import OrderedDict

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueTogetherValidator

from nautobot.core.api import (
    ChoiceField,
    NautobotHyperlinkedRelatedField,
    NautobotModelSerializer,
    ValidatedModelSerializer,
)
from nautobot.dcim.models.locations import Location
from nautobot.extras.api.mixins import TaggedModelSerializerMixin
from nautobot.ipam import constants
from nautobot.ipam.api.fields import IPFieldSerializer
from nautobot.ipam.choices import PrefixTypeChoices, ServiceProtocolChoices
from nautobot.ipam.models import (
    get_default_namespace,
    IPAddress,
    IPAddressToInterface,
    Namespace,
    Prefix,
    PrefixLocationAssignment,
    RIR,
    RouteTarget,
    Service,
    VLAN,
    VLANGroup,
    VLANLocationAssignment,
    VRF,
    VRFDeviceAssignment,
    VRFPrefixAssignment,
)

#
# Namespaces
#


class NamespaceSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    class Meta:
        model = Namespace
        fields = "__all__"
        list_display_fields = ["name", "description", "location"]


#
# VRFs
#


class VRFSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    class Meta:
        model = VRF
        fields = "__all__"
        list_display_fields = ["name", "rd", "tenant", "description"]
        extra_kwargs = {"namespace": {"default": get_default_namespace}}


class VRFDeviceAssignmentSerializer(ValidatedModelSerializer):
    class Meta:
        model = VRFDeviceAssignment
        fields = "__all__"
        validators = []

    def validate(self, data):
        if data.get("device"):
            validator = UniqueTogetherValidator(queryset=VRFDeviceAssignment.objects.all(), fields=("device", "vrf"))
            validator(data, self)
        if data.get("virtual_machine"):
            validator = UniqueTogetherValidator(
                queryset=VRFDeviceAssignment.objects.all(), fields=("virtual_machine", "vrf")
            )
            validator(data, self)
        return super().validate(data)


class VRFPrefixAssignmentSerializer(ValidatedModelSerializer):
    class Meta:
        model = VRFPrefixAssignment
        fields = "__all__"


#
# Route targets
#


class RouteTargetSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    class Meta:
        model = RouteTarget
        fields = "__all__"
        list_display_fields = ["name", "tenant", "description"]


#
# RIRs
#


class RIRSerializer(NautobotModelSerializer):
    assigned_prefix_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = RIR
        fields = "__all__"
        list_display_fields = [
            "name",
            "is_private",
            "assigned_prefix_count",
            "description",
        ]


#
# VLANs
#


class VLANGroupSerializer(NautobotModelSerializer):
    vlan_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = VLANGroup
        fields = "__all__"
        list_display_fields = ["name", "location", "vlan_count", "description"]


class VLANSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    prefix_count = serializers.IntegerField(read_only=True)
    location = NautobotHyperlinkedRelatedField(
        allow_null=True,
        queryset=Location.objects.all(),
        required=False,
        view_name="dcim-api:location-detail",
        write_only=True,
    )

    class Meta:
        model = VLAN
        # TODO(jathan): These were taken from VLANDetailTable and not VLANTable. Let's make sure
        # these are correct.
        fields = "__all__"
        list_display_fields = [
            "vid",
            "locations",
            "vlan_group",
            "name",
            "prefixes",
            "tenant",
            "status",
            "role",
            "description",
        ]
        validators = []
        extra_kwargs = {"locations": {"read_only": True}}

    def validate(self, data):
        # Validate uniqueness of vid and name if a group has been assigned.
        if data.get("vlan_group", None):
            for field in ["vid", "name"]:
                validator = UniqueTogetherValidator(queryset=VLAN.objects.all(), fields=("vlan_group", field))
                validator(data, self)

        # Enforce model validation
        super().validate(data)

        return data


class VLANLegacySerializer(VLANSerializer):
    """
    This legacy serializer is used for API versions 2.0 and 2.1.
    And it is not longer valid for API version 2.2 and so on.
    """

    location = NautobotHyperlinkedRelatedField(
        allow_null=True, queryset=Location.objects.all(), required=False, view_name="dcim-api:location-detail"
    )

    class Meta:
        model = VLAN
        fields = [
            "id",
            "object_type",
            "display",
            "url",
            "natural_slug",
            "prefix_count",
            "vid",
            "name",
            "description",
            "vlan_group",
            "status",
            "role",
            "tenant",
            "location",
            "created",
            "last_updated",
            "tags",
            "notes_url",
            "custom_fields",
        ]
        validators = []


class VLANLocationAssignmentSerializer(ValidatedModelSerializer):
    class Meta:
        model = VLANLocationAssignment
        fields = "__all__"


#
# Prefixes
#


class PrefixSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    prefix = IPFieldSerializer()
    type = ChoiceField(choices=PrefixTypeChoices, default=PrefixTypeChoices.TYPE_NETWORK)
    # for backward compatibility with 2.0-2.1 where a Prefix had only a single Location
    location = NautobotHyperlinkedRelatedField(
        allow_null=True,
        queryset=Location.objects.all(),
        required=False,
        view_name="dcim-api:location-detail",
        write_only=True,
    )

    class Meta:
        model = Prefix
        fields = "__all__"
        list_display_fields = [
            "prefix",
            "namespace",
            "type",
            "status",
            "vrf",
            "tenant",
            "locations",
            "vlan",
            "role",
            "description",
        ]
        extra_kwargs = {
            "ip_version": {"read_only": True},
            "namespace": {"default": get_default_namespace},
            "prefix_length": {"read_only": True},
            "locations": {"read_only": True},
        }

        detail_view_config = {
            "layout": [
                {
                    "Prefix": {
                        "fields": [
                            "prefix",
                            "parent",
                            "namespace",
                            "type",
                            "network",
                            "broadcast",
                            "prefix_length",
                            "ip_version",
                            "description",
                            "role",
                            "vlan",
                            "locations",
                            "tenant",
                            "rir",
                            "date_allocated",
                        ]
                    },
                },
            ],
        }


class PrefixLegacySerializer(PrefixSerializer):
    """Serializer for API versions 2.0-2.1 where a Prefix only had a single Location."""

    location = NautobotHyperlinkedRelatedField(
        allow_null=True, queryset=Location.objects.all(), required=False, view_name="dcim-api:location-detail"
    )

    class Meta(PrefixSerializer.Meta):
        fields = [
            "id",
            "object_type",
            "display",
            "url",
            "natural_slug",
            "prefix",
            "network",
            "broadcast",
            "prefix_length",
            "type",
            "status",
            "role",
            "parent",
            "ip_version",
            "location",
            "namespace",
            "tenant",
            "vlan",
            "rir",
            "date_allocated",
            "description",
            "created",
            "last_updated",
            "tags",
            "notes_url",
            "custom_fields",
        ]


class PrefixLocationAssignmentSerializer(ValidatedModelSerializer):
    class Meta:
        model = PrefixLocationAssignment
        fields = "__all__"


class PrefixLengthSerializer(serializers.Serializer):
    prefix_length = serializers.IntegerField()

    def to_internal_value(self, data):
        requested_prefix = data.get("prefix_length")
        if requested_prefix is None:
            raise serializers.ValidationError({"prefix_length": "this field can not be missing"})
        if not isinstance(requested_prefix, int):
            raise serializers.ValidationError({"prefix_length": "this field must be int type"})

        prefix = self.context.get("prefix")
        if prefix.ip_version == 4 and requested_prefix > 32:
            raise serializers.ValidationError({"prefix_length": f"Invalid prefix length ({requested_prefix}) for IPv4"})
        elif prefix.ip_version == 6 and requested_prefix > 128:
            raise serializers.ValidationError({"prefix_length": f"Invalid prefix length ({requested_prefix}) for IPv6"})
        return data


class AvailablePrefixSerializer(serializers.Serializer):
    """
    Representation of a prefix which does not exist in the database.
    """

    ip_version = serializers.IntegerField(read_only=True)
    prefix = serializers.CharField(read_only=True)

    def to_representation(self, instance):
        return OrderedDict(
            [
                ("ip_version", instance.version),
                ("prefix", str(instance)),
            ]
        )


#
# IP addresses
#


class IPAddressSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    address = IPFieldSerializer()
    # namespace is not a model field, so we have to specify it explicitly
    namespace = NautobotHyperlinkedRelatedField(
        view_name="ipam-api:namespace-detail", write_only=True, queryset=Namespace.objects.all(), required=False
    )

    class Meta:
        model = IPAddress
        fields = "__all__"
        list_display_fields = [
            "address",
            "type",
            "vrf",
            "status",
            "role",
            "tenant",
            "dns_name",
            "description",
        ]
        extra_kwargs = {
            "ip_version": {"read_only": True},
            "mask_length": {"read_only": True},
            "nat_outside_list": {"read_only": True},
            "parent": {"required": False},
        }

        detail_view_config = {
            "layout": [
                {
                    "IP Address": {
                        "fields": [
                            # FixMe(timizuo): Missing in new-ui; resolve when working on #4355
                            "namespace",
                            "ip_version",
                            "type",
                            "role",
                            "dns_name",
                            "description",
                        ]
                    },
                    "Operational Details": {
                        "fields": [
                            "tenant",
                            "assigned",  # FixMe(timizuo) Missing in new-ui; resolve when working on #4355
                            "nat_inside",
                            "nat_outside_list",
                        ]
                    },
                },
            ],
        }

    def validate(self, data):
        namespace = data.get("namespace", None)
        parent = data.get("parent", None)

        # Only assert namespace/parent on create.
        if self.instance is None and not any([namespace, parent]):
            raise ValidationError({"__all__": "One of parent or namespace must be provided"})

        super().validate(data)
        return data

    def get_field_names(self, declared_fields, info):
        """Add reverse relations to the automatically discovered fields."""
        fields = list(super().get_field_names(declared_fields, info))
        self.extend_field_names(fields, "nat_outside_list")
        self.extend_field_names(fields, "interfaces")
        self.extend_field_names(fields, "vm_interfaces")
        return fields


class AvailableIPSerializer(serializers.Serializer):
    """
    Representation of an IP address which does not exist in the database.
    """

    ip_version = serializers.IntegerField(read_only=True)
    address = serializers.CharField(read_only=True)

    def to_representation(self, instance):
        return OrderedDict(
            [
                ("ip_version", self.context["prefix"].version),
                ("address", f"{instance}/{self.context['prefix'].prefixlen}"),
            ]
        )


#
# IP address to interface
#


class IPAddressToInterfaceSerializer(ValidatedModelSerializer):
    class Meta:
        model = IPAddressToInterface
        fields = "__all__"
        validators = []

    def validate(self, data):
        # Validate uniqueness of (parent, name) since we omitted the automatically created validator from Meta.
        if data.get("interface"):
            validator = UniqueTogetherValidator(
                queryset=IPAddressToInterface.objects.all(), fields=("interface", "ip_address")
            )
            validator(data, self)
        if data.get("vm_interface"):
            validator = UniqueTogetherValidator(
                queryset=IPAddressToInterface.objects.all(), fields=("vm_interface", "ip_address")
            )
            validator(data, self)
        return super().validate(data)


#
# Services
#


class ServiceSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    # TODO #3024 make a backlog item to rip out the choice field.
    protocol = ChoiceField(choices=ServiceProtocolChoices, required=False)
    ports = serializers.ListField(
        child=serializers.IntegerField(
            min_value=constants.SERVICE_PORT_MIN,
            max_value=constants.SERVICE_PORT_MAX,
        ),
    )

    class Meta:
        model = Service
        fields = "__all__"
        extra_kwargs = {
            "device": {"help_text": "Required if no virtual_machine is specified"},
            "virtual_machine": {"help_text": "Required if no device is specified"},
        }
        # TODO(jathan): We need to account for the "parent" field from the `ServiceTable` which is
        # an either/or column for `device` or `virtual_machine`. For now it's hard-coded to
        # `device`.
        # list_display_fields = ["name", "parent", "protocol", "ports", "description"]
        list_display_fields = ["name", "device", "protocol", "ports", "description"]
