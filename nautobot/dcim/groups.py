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

    field_order = ["platform", "manufacturer", "device_type_id", "role", "site", "tag"]


class SiteDynamicGroupMap(BaseDynamicGroupMap):

    model = Site
    filterset = SiteFilterSet
    filterform = SiteFilterForm

    field_order = ["tag"]
