from django import forms
from django.contrib.contenttypes.models import ContentType

from nautobot.dcim.models import Region, Site, Location
from nautobot.utilities.forms import CSVModelChoiceField, DynamicModelChoiceField, DynamicModelMultipleChoiceField


class LocatableModelFormMixin(forms.Form):
    """
    Mixin for model forms that can link to a Site (filtered by Region) and/or Location.

    In the long term when Region and Site are collapsed into Location this should greatly reduce the number
    of distinct places in the code that we need to touch.
    """

    region = DynamicModelChoiceField(
        queryset=Region.objects.all(),
        required=False,
        initial_params={"sites": "$site"},
    )
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        query_params={"region_id": "$region"},
    )
    location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        query_params={"base_site": "$site"},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set the `required` flag on the `site` field and widget based on the model attributes
        self.fields["site"].required = not (self.Meta.model.site.field.null and self.Meta.model.site.field.blank)
        self.fields["site"].widget.attrs["required"] = self.fields["site"].required

        # Filter the `location` widget to only select locations that permit this content-type
        self.fields["location"].widget.add_query_param("content_type", self.Meta.model._meta.label_lower)
        self.fields["location"].queryset = Location.objects.filter(
            location_type__content_types=ContentType.objects.get_for_model(self.Meta.model)
        )


class LocatableModelBulkEditFormMixin(forms.Form):
    """
    Mixin for model bulk-edit forms that can link to a Site (filtered by Region) and/or Location.

    In the long term when Region and Site are collapsed into Location this should greatly reduce the number
    of distinct places in the code that we need to touch.
    """

    region = DynamicModelChoiceField(
        queryset=Region.objects.all(),
        required=False,
        initial_params={"sites": "$site"},
    )
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        query_params={"region_id": "$region"},
    )
    location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        query_params={"base_site": "$site"},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter the `location` widget to only select locations that permit this content-type
        self.fields["location"].widget.add_query_param("content_type", self.Meta.model._meta.label_lower)
        self.fields["location"].queryset = Location.objects.filter(
            location_type__content_types=ContentType.objects.get_for_model(self.Meta.model)
        )


class LocatableModelCSVFormMixin(forms.Form):
    """
    Mixin for CSV forms that can be associated to a Site and optional Location.

    In the long term when Region and Site are collapsed into Location this should greatly reduce the number
    of distinct places in the code that we need to touch.
    """

    site = CSVModelChoiceField(
        queryset=Site.objects.all(),
        to_field_name="name",
        help_text="Assigned site",
    )
    location = CSVModelChoiceField(
        queryset=Location.objects.all(),
        to_field_name="name",
        required=False,
        help_text="Assigned location",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set the `required` flag on the `site` field and widget based on the model attributes
        self.fields["site"].required = not (self.Meta.model.site.field.null and self.Meta.model.site.field.blank)
        self.fields["site"].widget.attrs["required"] = self.fields["site"].required

        # Filter the `location` widget to only select locations that permit this content-type
        self.fields["location"].queryset = Location.objects.filter(
            location_type__content_types=ContentType.objects.get_for_model(self.Meta.model)
        )


class LocatableModelFilterFormMixin(forms.Form):
    """
    Mixin for filterset forms that can filter by Site, Region, and/or Location.

    Can even be used with models that *do not have* these fields, so long as the filterset *does have* such filters.

    In the long term when Region and Site are collapsed into Location this should greatly reduce the number
    of distinct places in the code that we need to touch.
    """

    region = DynamicModelMultipleChoiceField(
        queryset=Region.objects.all(),
        to_field_name="slug",
        required=False,
    )
    site = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        to_field_name="slug",
        required=False,
        null_option="None",
        query_params={"region": "$region"},
    )
    location = DynamicModelMultipleChoiceField(
        queryset=Location.objects.all(),
        to_field_name="slug",
        required=False,
        null_option="None",
        query_params={"base_site": "$site"},
    )
