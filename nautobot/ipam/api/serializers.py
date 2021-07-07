from collections import OrderedDict

from django.contrib.contenttypes.models import ContentType
from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from nautobot.core.api import (
    ChoiceField,
    ContentTypeField,
    SerializedPKRelatedField,
)
from nautobot.dcim.api.nested_serializers import (
    NestedDeviceSerializer,
    NestedSiteSerializer,
)
from nautobot.extras.api.customfields import CustomFieldModelSerializer
from nautobot.extras.api.serializers import (
    StatusModelSerializerMixin,
    TaggedObjectSerializer,
)
from nautobot.ipam.choices import *
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
from .nested_serializers import *


#
# VRFs
#


class VRFSerializer(TaggedObjectSerializer, CustomFieldModelSerializer):
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
            "id",
            "url",
            "name",
            "rd",
            "tenant",
            "enforce_unique",
            "description",
            "import_targets",
            "export_targets",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "ipaddress_count",
            "prefix_count",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


#
# Route targets
#


class RouteTargetSerializer(TaggedObjectSerializer, CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:routetarget-detail")
    tenant = NestedTenantSerializer(required=False, allow_null=True)

    class Meta:
        model = RouteTarget
        fields = [
            "id",
            "url",
            "name",
            "tenant",
            "description",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


#
# RIRs/aggregates
#


class RIRSerializer(CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:rir-detail")
    aggregate_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = RIR
        fields = [
            "id",
            "url",
            "name",
            "slug",
            "is_private",
            "description",
            "aggregate_count",
            "custom_fields",
            "created",
            "last_updated",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


class AggregateSerializer(TaggedObjectSerializer, CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:aggregate-detail")
    family = ChoiceField(choices=IPAddressFamilyChoices, read_only=True)
    prefix = IPFieldSerializer()
    rir = NestedRIRSerializer()
    tenant = NestedTenantSerializer(required=False, allow_null=True)

    class Meta:
        model = Aggregate
        fields = [
            "id",
            "url",
            "family",
            "prefix",
            "rir",
            "tenant",
            "date_added",
            "description",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "computed_fields",
        ]
        read_only_fields = ["family"]
        opt_in_fields = ["computed_fields"]


#
# VLANs
#


class RoleSerializer(CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:role-detail")
    prefix_count = serializers.IntegerField(read_only=True)
    vlan_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Role
        fields = [
            "id",
            "url",
            "name",
            "slug",
            "weight",
            "description",
            "prefix_count",
            "vlan_count",
            "custom_fields",
            "created",
            "last_updated",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


class VLANGroupSerializer(CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:vlangroup-detail")
    site = NestedSiteSerializer(required=False, allow_null=True)
    vlan_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = VLANGroup
        fields = [
            "id",
            "url",
            "name",
            "slug",
            "site",
            "description",
            "vlan_count",
            "custom_fields",
            "created",
            "last_updated",
            "computed_fields",
        ]
        validators = []
        opt_in_fields = ["computed_fields"]

    def validate(self, data):

        # Validate uniqueness of name and slug if a site has been assigned.
        if data.get("site", None):
            for field in ["name", "slug"]:
                validator = UniqueTogetherValidator(queryset=VLANGroup.objects.all(), fields=("site", field))
                validator(data, self)

        # Enforce model validation
        super().validate(data)

        return data


class VLANSerializer(TaggedObjectSerializer, StatusModelSerializerMixin, CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:vlan-detail")
    site = NestedSiteSerializer(required=False, allow_null=True)
    group = NestedVLANGroupSerializer(required=False, allow_null=True)
    tenant = NestedTenantSerializer(required=False, allow_null=True)
    role = NestedRoleSerializer(required=False, allow_null=True)
    prefix_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = VLAN
        fields = [
            "id",
            "url",
            "site",
            "group",
            "vid",
            "name",
            "tenant",
            "status",
            "role",
            "description",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "prefix_count",
            "computed_fields",
        ]
        validators = []
        opt_in_fields = ["computed_fields"]

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


class PrefixSerializer(TaggedObjectSerializer, StatusModelSerializerMixin, CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:prefix-detail")
    family = ChoiceField(choices=IPAddressFamilyChoices, read_only=True)
    prefix = IPFieldSerializer()
    site = NestedSiteSerializer(required=False, allow_null=True)
    vrf = NestedVRFSerializer(required=False, allow_null=True)
    tenant = NestedTenantSerializer(required=False, allow_null=True)
    vlan = NestedVLANSerializer(required=False, allow_null=True)
    role = NestedRoleSerializer(required=False, allow_null=True)

    class Meta:
        model = Prefix
        fields = [
            "id",
            "url",
            "family",
            "prefix",
            "site",
            "vrf",
            "tenant",
            "vlan",
            "status",
            "role",
            "is_pool",
            "description",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "computed_fields",
        ]
        read_only_fields = ["family"]
        opt_in_fields = ["computed_fields"]


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
            raise serializers.ValidationError(
                {"prefix_length": "Invalid prefix length ({}) for IPv4".format((requested_prefix))}
            )
        elif prefix.family == 6 and requested_prefix > 128:
            raise serializers.ValidationError(
                {"prefix_length": "Invalid prefix length ({}) for IPv6".format((requested_prefix))}
            )
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


class IPAddressSerializer(TaggedObjectSerializer, StatusModelSerializerMixin, CustomFieldModelSerializer):
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
    nat_outside = NestedIPAddressSerializer(read_only=True)

    class Meta:
        model = IPAddress
        fields = [
            "id",
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
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "computed_fields",
        ]
        read_only_fields = ["family"]
        opt_in_fields = ["computed_fields"]

    @swagger_serializer_method(serializer_or_field=serializers.DictField)
    def get_assigned_object(self, obj):
        if obj.assigned_object is None:
            return None
        serializer = get_serializer_for_model(obj.assigned_object, prefix="Nested")
        context = {"request": self.context["request"]}
        return serializer(obj.assigned_object, context=context).data


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
                ("address", "{}/{}".format(instance, self.context["prefix"].prefixlen)),
                ("vrf", vrf),
            ]
        )


#
# Services
#


class ServiceSerializer(TaggedObjectSerializer, CustomFieldModelSerializer):
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
            "id",
            "url",
            "device",
            "virtual_machine",
            "name",
            "ports",
            "protocol",
            "ipaddresses",
            "description",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]
