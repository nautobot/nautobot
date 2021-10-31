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
from .models import Device, Site, DeviceRole
from .filters import DeviceFilterSet


class DeviceDynamicGroupMap:

    model = Device
    filterset = DeviceFilterSet

    field_order = ["role", "site", "tag"]

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

    tag: TagFilterField(model)

    @classmethod
    def get_queryset(cls, filter):
        """Return a queryset matching the dynamic group filter.

        By default the queryset is generated based of the filterset but this is not mandatory
        """
        filterset = cls.filterset(cls.get_filterset_params(filter), cls.model.objects.all())
        return filterset.qs

    @classmethod
    def get_filterset_params(cls, filter):
        return filter

    @classmethod
    def get_filterset_as_string(cls, filter):
        """Get filterset as string."""
        if not filter:
            return None

        result = ""
        # separator = ""

        for key, value in cls.get_filterset_params(filter).items():
            if isinstance(value, list):
                for item in value:
                    if result != "":
                        result += "&"
                    result += f"{key}={item}"
            else:
                result += "&"
                result += f"{key}={value}"

        return result

    @classmethod
    def get_group_queryset_filter(cls, obj):

        dynamicgroup_filter = Q(filter__role__contains=obj.device_role.slug) | Q(filter__site__contains=obj.site.slug)

        return dynamicgroup_filter
