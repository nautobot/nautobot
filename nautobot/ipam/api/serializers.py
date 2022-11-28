from collections import OrderedDict

from django.contrib.contenttypes.models import ContentType
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from nautobot.core.api import (
    ChoiceField,
    ContentTypeField,
    SerializedPKRelatedField,
)
from nautobot.dcim.api.nested_serializers import (
    NestedDeviceSerializer,
    NestedLocationSerializer,
    NestedSiteSerializer,
)
from nautobot.extras.api.serializers import (
    NautobotModelSerializer,
    StatusModelSerializerMixin,
    TaggedModelSerializerMixin,
)
from nautobot.ipam.choices import IPAddressFamilyChoices, IPAddressRoleChoices, ServiceProtocolChoices
from nautobot.ipam import constants
from nautobot.ipam.models import (
    Aggregate,
    IPAddress,
    Prefix,
    RIR,
    Role,
    RouteTarget,
    Service,
    VLAN,
    VLANGroup,
    VRF,
)
from nautobot.tenancy.api.nested_serializers import NestedTenantSerializer
from nautobot.utilities.api import get_serializer_for_model
from nautobot.virtualization.api.nested_serializers import (
    NestedVirtualMachineSerializer,
)

# Not all of these variable(s) are not actually used anywhere in this file, but required for the
# automagically replacing a Serializer with its corresponding NestedSerializer.
from .nested_serializers import (  # noqa: F401
    IPFieldSerializer,
    NestedAggregateSerializer,
    NestedIPAddressSerializer,
    NestedPrefixSerializer,
    NestedRIRSerializer,
    NestedRoleSerializer,
    NestedRouteTargetSerializer,
    NestedServiceSerializer,
    NestedVLANGroupSerializer,
    NestedVLANSerializer,
    NestedVRFSerializer,
)

#
# VRFs
#


class VRFSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:vrf-detail")
    tenant = NestedTenantSerializer(required=False, allow_null=True)
    import_targets = SerializedPKRelatedField(
        queryset=RouteTarget.objects.all(),
        serializer=NestedRouteTargetSerializer,
        required=False,
        many=True,
    )
    export_targets = SerializedPKRelatedField(
        queryset=RouteTarget.objects.all(),
        serializer=NestedRouteTargetSerializer,
        required=False,
        many=True,
    )
    ipaddress_count = serializers.IntegerField(read_only=True)
    prefix_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = VRF
        fields = [
            "url",
            "name",
            "rd",
            "tenant",
            "enforce_unique",
            "description",
            "import_targets",
            "export_targets",
            "ipaddress_count",
            "prefix_count",
        ]


#
# Route targets
#


class RouteTargetSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:routetarget-detail")
    tenant = NestedTenantSerializer(required=False, allow_null=True)

    class Meta:
        model = RouteTarget
        fields = [
            "url",
            "name",
            "tenant",
            "description",
        ]


#
# RIRs/aggregates
#


class RIRSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:rir-detail")
    aggregate_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = RIR
        fields = [
            "url",
            "name",
            "slug",
            "is_private",
            "description",
            "aggregate_count",
        ]


class AggregateSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:aggregate-detail")
    family = ChoiceField(choices=IPAddressFamilyChoices, read_only=True)
    prefix = IPFieldSerializer()
    rir = NestedRIRSerializer()
    tenant = NestedTenantSerializer(required=False, allow_null=True)

    class Meta:
        model = Aggregate
        fields = [
            "url",
            "family",
            "prefix",
            "rir",
            "tenant",
            "date_added",
            "description",
        ]
        read_only_fields = ["family"]


#
# VLANs
#


class RoleSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:role-detail")
    prefix_count = serializers.IntegerField(read_only=True)
    vlan_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Role
        fields = [
            "url",
            "name",
            "slug",
            "weight",
            "description",
            "prefix_count",
            "vlan_count",
        ]


class VLANGroupSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:vlangroup-detail")
    site = NestedSiteSerializer(required=False, allow_null=True)
    location = NestedLocationSerializer(required=False, allow_null=True)
    vlan_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = VLANGroup
        fields = [
            "url",
            "name",
            "slug",
            "site",
            "location",
            "description",
            "vlan_count",
        ]
        # 2.0 TODO: Remove if/when slug is globally unique. This would be a breaking change.
        validators = []

    def validate(self, data):

        # Validate uniqueness of name and slug if a site has been assigned.
        # 2.0 TODO: Remove if/when slug is globally unique. This would be a breaking change.
        if data.get("site", None):
            for field in ["name", "slug"]:
                validator = UniqueTogetherValidator(queryset=VLANGroup.objects.all(), fields=("site", field))
                validator(data, self)

        # Enforce model validation
        super().validate(data)

        return data


class VLANSerializer(NautobotModelSerializer, TaggedModelSerializerMixin, StatusModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:vlan-detail")
    site = NestedSiteSerializer(required=False, allow_null=True)
    location = NestedLocationSerializer(required=False, allow_null=True)
    group = NestedVLANGroupSerializer(required=False, allow_null=True)
    tenant = NestedTenantSerializer(required=False, allow_null=True)
    role = NestedRoleSerializer(required=False, allow_null=True)
    prefix_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = VLAN
        fields = [
            "url",
            "site",
            "location",
            "group",
            "vid",
            "name",
            "tenant",
            "status",
            "role",
            "description",
            "prefix_count",
        ]
        validators = []

    def validate(self, data):

        # Validate uniqueness of vid and name if a group has been assigned.
        if data.get("group", None):
            for field in ["vid", "name"]:
                validator = UniqueTogetherValidator(queryset=VLAN.objects.all(), fields=("group", field))
                validator(data, self)

        # Enforce model validation
        super().validate(data)

        return data


#
# Prefixes
#


class PrefixSerializer(NautobotModelSerializer, TaggedModelSerializerMixin, StatusModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:prefix-detail")
    family = ChoiceField(choices=IPAddressFamilyChoices, read_only=True)
    prefix = IPFieldSerializer()
    site = NestedSiteSerializer(required=False, allow_null=True)
    location = NestedLocationSerializer(required=False, allow_null=True)
    vrf = NestedVRFSerializer(required=False, allow_null=True)
    tenant = NestedTenantSerializer(required=False, allow_null=True)
    vlan = NestedVLANSerializer(required=False, allow_null=True)
    role = NestedRoleSerializer(required=False, allow_null=True)

    class Meta:
        model = Prefix
        fields = [
            "url",
            "family",
            "prefix",
            "site",
            "location",
            "vrf",
            "tenant",
            "vlan",
            "status",
            "role",
            "is_pool",
            "description",
        ]
        read_only_fields = ["family"]


class PrefixLengthSerializer(serializers.Serializer):

    prefix_length = serializers.IntegerField()

    def to_internal_value(self, data):
        requested_prefix = data.get("prefix_length")
        if requested_prefix is None:
            raise serializers.ValidationError({"prefix_length": "this field can not be missing"})
        if not isinstance(requested_prefix, int):
            raise serializers.ValidationError({"prefix_length": "this field must be int type"})

        prefix = self.context.get("prefix")
        if prefix.family == 4 and requested_prefix > 32:
            raise serializers.ValidationError({"prefix_length": f"Invalid prefix length ({requested_prefix}) for IPv4"})
        elif prefix.family == 6 and requested_prefix > 128:
            raise serializers.ValidationError({"prefix_length": f"Invalid prefix length ({requested_prefix}) for IPv6"})
        return data


class AvailablePrefixSerializer(serializers.Serializer):
    """
    Representation of a prefix which does not exist in the database.
    """

    family = serializers.IntegerField(read_only=True)
    prefix = serializers.CharField(read_only=True)
    vrf = NestedVRFSerializer(read_only=True)

    def to_representation(self, instance):
        if self.context.get("vrf"):
            vrf = NestedVRFSerializer(self.context["vrf"], context={"request": self.context["request"]}).data
        else:
            vrf = None
        return OrderedDict(
            [
                ("family", instance.version),
                ("prefix", str(instance)),
                ("vrf", vrf),
            ]
        )


#
# IP addresses
#


class IPAddressSerializer(NautobotModelSerializer, TaggedModelSerializerMixin, StatusModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:ipaddress-detail")
    family = ChoiceField(choices=IPAddressFamilyChoices, read_only=True)
    address = IPFieldSerializer()
    vrf = NestedVRFSerializer(required=False, allow_null=True)
    tenant = NestedTenantSerializer(required=False, allow_null=True)
    role = ChoiceField(choices=IPAddressRoleChoices, allow_blank=True, required=False)
    assigned_object_type = ContentTypeField(
        queryset=ContentType.objects.filter(constants.IPADDRESS_ASSIGNMENT_MODELS),
        required=False,
        allow_null=True,
    )
    assigned_object = serializers.SerializerMethodField(read_only=True)
    nat_inside = NestedIPAddressSerializer(required=False, allow_null=True)
    nat_outside = NestedIPAddressSerializer(read_only=True, many=True, source="nat_outside_list")

    class Meta:
        model = IPAddress
        fields = [
            "url",
            "family",
            "address",
            "vrf",
            "tenant",
            "status",
            "role",
            "assigned_object_type",
            "assigned_object_id",
            "assigned_object",
            "nat_inside",
            "nat_outside",
            "dns_name",
            "description",
        ]
        read_only_fields = ["family"]

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_assigned_object(self, obj):
        if obj.assigned_object is None:
            return None
        serializer = get_serializer_for_model(obj.assigned_object, prefix="Nested")
        context = {"request": self.context["request"]}
        return serializer(obj.assigned_object, context=context).data


# 2.0 TODO: Remove in 2.0. Used to serialize against pre-1.3 behavior (nat_inside was one-to-one)
class IPAddressSerializerLegacy(IPAddressSerializer):
    nat_outside = NestedIPAddressSerializer(read_only=True)


class AvailableIPSerializer(serializers.Serializer):
    """
    Representation of an IP address which does not exist in the database.
    """

    family = serializers.IntegerField(read_only=True)
    address = serializers.CharField(read_only=True)
    vrf = NestedVRFSerializer(read_only=True)

    def to_representation(self, instance):
        if self.context.get("vrf"):
            vrf = NestedVRFSerializer(self.context["vrf"], context={"request": self.context["request"]}).data
        else:
            vrf = None
        return OrderedDict(
            [
                ("family", self.context["prefix"].version),
                ("address", f"{instance}/{self.context['prefix'].prefixlen}"),
                ("vrf", vrf),
            ]
        )


#
# Services
#


class ServiceSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:service-detail")
    device = NestedDeviceSerializer(required=False, allow_null=True)
    virtual_machine = NestedVirtualMachineSerializer(required=False, allow_null=True)
    protocol = ChoiceField(choices=ServiceProtocolChoices, required=False)
    ipaddresses = SerializedPKRelatedField(
        queryset=IPAddress.objects.all(),
        serializer=NestedIPAddressSerializer,
        required=False,
        many=True,
    )
    ports = serializers.ListField(
        child=serializers.IntegerField(
            min_value=constants.SERVICE_PORT_MIN,
            max_value=constants.SERVICE_PORT_MAX,
        )
    )

    class Meta:
        model = Service
        fields = [
            "url",
            "device",
            "virtual_machine",
            "name",
            "ports",
            "protocol",
            "ipaddresses",
            "description",
        ]
