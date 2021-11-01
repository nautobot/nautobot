from django.db.models import Q

from nautobot.utilities.forms import (
    APISelect,
    APISelectMultiple,
    add_blank_choice,
    BootstrapMixin,
    BulkEditNullBooleanSelect,
    ColorSelect,
    CommentField,
    CSVChoiceField,
    CSVContentTypeField,
    CSVModelChoiceField,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    ExpandableNameField,
    form_from_model,
    NumericArrayField,
    SelectWithPK,
    SmallTextarea,
    SlugField,
    StaticSelect2,
    StaticSelect2Multiple,
    TagFilterField,
)
from nautobot.extras.groups import BaseDynamicGroupMap
from nautobot.extras.models import Tag
from .models import Device, Region, Site, DeviceRole
from .filters import DeviceFilterSet, SiteFilterSet


class DeviceDynamicGroupMap(BaseDynamicGroupMap):

    model = Device
    filterset = DeviceFilterSet

    field_order = ["role", "site"]

    site = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        to_field_name="slug",
        required=False,
    )

    role = DynamicModelMultipleChoiceField(
        queryset=DeviceRole.objects.all(),
        to_field_name="slug",
        required=False,
    )

    tag = DynamicModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        to_field_name="slug",
        required=False,
    )

    @classmethod
    def get_group_queryset_filter(cls, obj):
        """Return a queryset filter matching this DynamicGroup parameters."""
        queryset_filter = Q(filter__role__contains=obj.device_role.slug)
        queryset_filter |= Q(filter__site__contains=obj.site.slug)

        for tag in obj.tags.slugs():
            queryset_filter |= Q(filter__tags__contains=tag)


        return queryset_filter

class SiteDynamicGroupMap(BaseDynamicGroupMap):

    model = Site
    filterset = SiteFilterSet

    field_order = ["region", "tag"]

    region = DynamicModelMultipleChoiceField(
        queryset=Region.objects.all(),
        to_field_name="slug",
        required=False,
    )

    tag = DynamicModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        to_field_name="slug",
        required=False,
    )

    @classmethod
    def get_group_queryset_filter(cls, obj):
        """Return a queryset filter matching this DynamicGroup parameters."""
        queryset_filter = Q(filter__region__contains=obj.region.slug)
        for tag in obj.tags.slugs():
            queryset_filter |= Q(filter__tags__contains=tag)

        return queryset_filter
