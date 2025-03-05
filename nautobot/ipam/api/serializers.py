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


#
# VRFs
#


class VRFSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    class Meta:
        model = VRF
        fields = "__all__"
        extra_kwargs = {"namespace": {"default": get_default_namespace}}


class VRFDeviceAssignmentSerializer(ValidatedModelSerializer):
    class Meta:
        model = VRFDeviceAssignment
        fields = "__all__"
        validators = []

    def validate(self, attrs):
        foreign_key_fields = ["device", "virtual_machine", "virtual_device_context"]
        for foreign_key in foreign_key_fields:
            if attrs.get(foreign_key):
                validator = UniqueTogetherValidator(
                    queryset=VRFDeviceAssignment.objects.all(), fields=(foreign_key, "vrf")
                )
                validator(attrs, self)
        return super().validate(attrs)


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


#
# RIRs
#


class RIRSerializer(NautobotModelSerializer):
    assigned_prefix_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = RIR
        fields = "__all__"


#
# VLANs
#


class VLANGroupSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    vlan_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = VLANGroup
        fields = "__all__"


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
        fields = "__all__"
        validators = []
        extra_kwargs = {"locations": {"read_only": True}}

    def validate(self, attrs):
        # Validate uniqueness of vid and name if a group has been assigned.
        if attrs.get("vlan_group", None):
            for field in ["vid", "name"]:
                validator = UniqueTogetherValidator(queryset=VLAN.objects.all(), fields=("vlan_group", field))
                validator(attrs, self)

        # Enforce model validation
        super().validate(attrs)

        return attrs


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

    def get_field_names(self, declared_fields, info):
        """Add reverse M2M for VRF's to the fields for this serializer."""
        field_names = list(super().get_field_names(declared_fields, info))
        self.extend_field_names(field_names, "vrfs")
        return field_names

    class Meta:
        model = Prefix
        fields = "__all__"
        extra_kwargs = {
            "ip_version": {"read_only": True},
            "namespace": {"default": get_default_namespace},
            "prefix_length": {"read_only": True},
            "locations": {"read_only": True},
            "vrfs": {"read_only": True},
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


class PrefixLengthSerializer(PrefixLegacySerializer):
    """
    Input serializer for POST to /api/ipam/prefixes/<id>/available-prefixes/, i.e. allocating one or more sub-prefixes.

    Since setting of multiple locations on create is not supported, this uses the legacy single-location option.
    """

    prefix_length = serializers.IntegerField(required=True)

    class Meta(PrefixLegacySerializer.Meta):
        fields = PrefixLegacySerializer.Meta.fields.copy()
        fields.remove("prefix")
        fields.remove("network")
        fields.remove("broadcast")
        fields.remove("parent")
        fields.remove("ip_version")
        fields.remove("namespace")


class AvailablePrefixSerializer(serializers.Serializer):
    """
    Representation of a prefix which does not exist in the database.

    Response serializer for a GET to /api/ipam/prefixes/<id>/available-prefixes/.
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
        extra_kwargs = {
            "ip_version": {"read_only": True},
            "mask_length": {"read_only": True},
            "nat_outside_list": {"read_only": True},
            "parent": {"required": False},
        }

    def validate(self, attrs):
        namespace = attrs.get("namespace", None)
        parent = attrs.get("parent", None)

        # Only assert namespace/parent on create.
        if self.instance is None and not any([namespace, parent]):
            raise ValidationError({"__all__": "One of parent or namespace must be provided"})

        super().validate(attrs)
        return attrs

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

    Response serializer for a GET to /api/ipam/prefixes/<id>/available-ips/.
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


class IPAllocationSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    """
    Input serializer for POST to /api/ipam/prefixes/<id>/available-ips/, i.e. allocating addresses from a prefix.
    """

    class Meta:
        model = IPAddress
        fields = (
            # not address/namespace/parent as those are implied by the selected prefix
            "status",
            "type",
            "dns_name",
            "description",
            "role",
            "tenant",
            "nat_inside",
            "tags",
            "custom_fields",
        )

    def validate(self, attrs):
        attrs["mask_length"] = self.context["prefix"].prefix_length
        return super().validate(attrs)


class VLANAllocationSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    """
    Input serializer for POST to /api/ipam/vlan-groups/<id>/available-vlans/, i.e. allocating VLAN from VLANGroup.
    """

    vid = serializers.IntegerField(required=False, min_value=constants.VLAN_VID_MIN, max_value=constants.VLAN_VID_MAX)

    def validate(self, attrs):
        """
        Skip `ValidatedModel` validation.

        This allows to skip `vid` attribute of `VLAN` model, while validate name and status.
        """
        return attrs

    class Meta(VLANSerializer.Meta):
        model = VLAN
        fields = (
            # permit "vid" and "vlan_group" for `VLAN` consistency.
            # validate them under `VLANGroupViewSet`
            "vid",
            "vlan_group",
            "name",
            "status",
            "role",
            "tenant",
            "description",
            "custom_fields",
        )


#
# IP address to interface
#


class IPAddressToInterfaceSerializer(ValidatedModelSerializer):
    class Meta:
        model = IPAddressToInterface
        fields = "__all__"
        validators = []

    def validate(self, attrs):
        # Validate uniqueness of (parent, name) since we omitted the automatically created validator from Meta.
        if attrs.get("interface"):
            validator = UniqueTogetherValidator(
                queryset=IPAddressToInterface.objects.all(), fields=("interface", "ip_address")
            )
            validator(attrs, self)
        if attrs.get("vm_interface"):
            validator = UniqueTogetherValidator(
                queryset=IPAddressToInterface.objects.all(), fields=("vm_interface", "ip_address")
            )
            validator(attrs, self)
        return super().validate(attrs)


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
        validators = []
        extra_kwargs = {
            "device": {"help_text": "Required if no virtual_machine is specified"},
            "virtual_machine": {"help_text": "Required if no device is specified"},
        }

    def validate(self, attrs):
        if attrs.get("device"):
            validator = UniqueTogetherValidator(queryset=Service.objects.all(), fields=("name", "device"))
            validator(attrs, self)
        if attrs.get("virtual_machine"):
            validator = UniqueTogetherValidator(queryset=Service.objects.all(), fields=("name", "virtual_machine"))
            validator(attrs, self)
        return super().validate(attrs)
