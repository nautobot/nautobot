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
from .forms import DeviceFilterForm, SiteFilterForm


class DeviceDynamicGroupMap(BaseDynamicGroupMap):

    model = Device
    filterset = DeviceFilterSet
    filterform = DeviceFilterForm

    field_order = ["platform", "role", "site"]

    # @classmethod
    # def get_queryset_filter(cls, obj):
    #     """Return a queryset filter matching this DynamicGroup parameters."""

    #     queryset_filter = Q()

    #     for field_name in cls.field_order:
    #         class_name = f"get_queryset_filter_default"
    #         if hasattr(cls, f"get_queryset_filter_{field_name}"):
    #             class_name = f"get_queryset_filter_{field_name}"

    #     queryset_filter |= getattr(cls, class_name)(field_name, )

    #     queryset_filter |= Q(filter__role__contains=obj.device_role.slug)
    #     queryset_filter |= Q(filter__site__contains=obj.site.slug)
    #     queryset_filter |= Q(filter__platform__contains=obj.platform.slug)

    #     queryset_filter |= Q(filter__region__contains=obj.site.region.slug)

    #     if obj.site.region.parent:
    #         queryset_filter = Q(filter__region__contains=obj.site.region.parent.slug)

    #     for tag in obj.tags.slugs():
    #         queryset_filter |= Q(filter__tags__contains=tag)

    #     return queryset_filter


class SiteDynamicGroupMap(BaseDynamicGroupMap):

    model = Site
    filterset = SiteFilterSet
    filterform = SiteFilterForm

    field_order = ["region"]

    # region = DynamicModelMultipleChoiceField(
    #     queryset=Region.objects.all(),
    #     to_field_name="slug",
    #     required=False,
    # )

    # tag = DynamicModelMultipleChoiceField(
    #     queryset=Tag.objects.all(),
    #     to_field_name="slug",
    #     required=False,
    # )

    # @classmethod
    # def get_queryset_filter(cls, obj):
    #     """Return a queryset filter matching this DynamicGroup parameters."""
    #     queryset_filter = Q(filter__region__contains=obj.region.slug)

    #     if obj.region.parent:
    #         queryset_filter = Q(filter__region__contains=obj.region.parent.slug)

    #     for tag in obj.tags.slugs():
    #         queryset_filter |= Q(filter__tag__contains=tag)

    #     return queryset_filter
