from django.contrib.contenttypes.models import ContentType
from django import forms

from nautobot.core.models.dynamic_groups import DynamicGroup, DynamicGroupMembership
from nautobot.extras.forms.base import NautobotModelForm
from nautobot.extras.utils import FeatureQuery
from nautobot.utilities.forms import (
    BootstrapMixin,
    CSVContentTypeField,
    DynamicModelChoiceField,
    MultipleContentTypeField,
    SlugField,
    StaticSelect2,
)

OBJ_TYPE_CHOICES = (
    ("", "All Objects"),
    (
        "Circuits",
        (
            ("provider", "Providers"),
            ("circuit", "Circuits"),
        ),
    ),
    (
        "DCIM",
        (
            ("site", "Sites"),
            ("rack", "Racks"),
            ("rackgroup", "Rack Groups"),
            ("devicetype", "Device types"),
            ("device", "Devices"),
            ("virtualchassis", "Virtual Chassis"),
            ("cable", "Cables"),
            ("powerfeed", "Power Feeds"),
        ),
    ),
    (
        "IPAM",
        (
            ("vrf", "VRFs"),
            ("aggregate", "Aggregates"),
            ("prefix", "Prefixes"),
            ("ipaddress", "IP addresses"),
            ("vlan", "VLANs"),
        ),
    ),
    ("Tenancy", (("tenant", "Tenants"),)),
    (
        "Virtualization",
        (
            ("cluster", "Clusters"),
            ("virtualmachine", "Virtual machines"),
        ),
    ),
)


class SearchForm(BootstrapMixin, forms.Form):
    q = forms.CharField(label="Search")
    obj_type = forms.ChoiceField(choices=OBJ_TYPE_CHOICES, required=False, label="Type")

    def __init__(self, *args, q_placeholder=None, **kwargs):
        super().__init__(*args, **kwargs)

        if q_placeholder:
            self.fields["q"].widget.attrs["placeholder"] = q_placeholder


#
# Dynamic Groups
#


class DynamicGroupForm(NautobotModelForm):
    """DynamicGroup model form."""

    slug = SlugField()
    content_type = CSVContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("dynamic_groups").get_query()).order_by("app_label", "model"),
        label="Content Type",
    )

    class Meta:
        model = DynamicGroup
        fields = [
            "name",
            "slug",
            "description",
            "content_type",
        ]


class DynamicGroupMembershipFormSetForm(forms.ModelForm):
    """DynamicGroupMembership model form for use inline on DynamicGroupFormSet."""

    group = DynamicModelChoiceField(
        queryset=DynamicGroup.objects.all(),
        query_params={"content_type": "$content_type"},
    )

    class Meta:
        model = DynamicGroupMembership
        fields = ("operator", "group", "weight")


# Inline formset for use with providing dynamic rows when creating/editing memberships of child
# DynamicGroups to a parent DynamicGroup.
BaseDynamicGroupMembershipFormSet = forms.inlineformset_factory(
    parent_model=DynamicGroup,
    model=DynamicGroupMembership,
    form=DynamicGroupMembershipFormSetForm,
    extra=4,
    fk_name="parent_group",
    widgets={
        "operator": StaticSelect2,
        "weight": forms.HiddenInput(),
    },
)


class DynamicGroupMembershipFormSet(BaseDynamicGroupMembershipFormSet):
    """
    Inline formset for use with providing dynamic rows when creating/editing memberships of child
    groups to a parent DynamicGroup.
    """


class DynamicGroupFilterForm(BootstrapMixin, forms.Form):
    """DynamicGroup filter form."""

    model = DynamicGroup
    q = forms.CharField(required=False, label="Search")
    content_type = MultipleContentTypeField(feature="dynamic_groups", choices_as_strings=True, label="Content Type")
