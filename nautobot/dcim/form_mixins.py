from django import forms
from django.contrib.contenttypes.models import ContentType

from nautobot.core.forms import DynamicModelChoiceField, DynamicModelMultipleChoiceField
from nautobot.dcim.models import Location


class LocatableModelFormMixin(forms.Form):
    """
    Mixin for model forms that can link to a Location.
    """

    location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set the `required` flag on the `location` field and widget based on the model attributes
        self.fields["location"].required = not (
            self.Meta.model.location.field.null and self.Meta.model.location.field.blank
        )
        self.fields["location"].widget.attrs["required"] = self.fields["location"].required

        # Filter the `location` widget to only select locations that permit this content-type
        self.fields["location"].widget.add_query_param("content_type", self.Meta.model._meta.label_lower)
        self.fields["location"].queryset = Location.objects.filter(
            location_type__content_types=ContentType.objects.get_for_model(self.Meta.model)
        )


class LocatableModelBulkEditFormMixin(forms.Form):
    """
    Mixin for model bulk-edit forms that can link to a Location.
    """

    location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter the `location` widget to only select locations that permit this content-type
        self.fields["location"].widget.add_query_param("content_type", self.Meta.model._meta.label_lower)
        self.fields["location"].queryset = Location.objects.filter(
            location_type__content_types=ContentType.objects.get_for_model(self.Meta.model)
        )


class LocatableModelFilterFormMixin(forms.Form):
    """
    Mixin for filterset forms that can filter by Location.

    Can even be used with models that *do not have* these fields, so long as the filterset *does have* such filters.
    """

    location = DynamicModelMultipleChoiceField(
        queryset=Location.objects.all(),
        to_field_name="name",
        required=False,
        null_option="None",
    )
