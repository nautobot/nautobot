from django import forms

from nautobot.apps.constants import CHARFIELD_MAX_LENGTH
from nautobot.apps.forms import (
    BootstrapMixin,
    BulkEditForm,
    NautobotBulkEditForm,
    NautobotModelForm,
    TagsBulkEditFormMixin,
)

from example_app.models import AnotherExampleModel, ExampleModel


class ExampleAppConfigForm(BootstrapMixin, forms.Form):
    """Example of what an App-specific configuration form might look like."""

    magic_word = forms.CharField()
    maximum_velocity = forms.IntegerField(help_text="Meters per second")


class ExampleModelForm(NautobotModelForm):
    """Generic create/update form for `ExampleModel` objects."""

    class Meta:
        model = ExampleModel
        fields = ["name", "number"]


class ExampleModelFilterForm(BootstrapMixin, forms.Form):
    """Filtering/search form for `ExampleModel` objects."""

    model = ExampleModel
    q = forms.CharField(required=False, label="Search")
    name = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    number = forms.IntegerField(required=False)


# This is purposefully inheriting from `NautobotBulkEditForm` then TagsBulkEditFormMixin to validate that MRO supports both orders now.
class ExampleModelBulkEditForm(NautobotBulkEditForm, TagsBulkEditFormMixin):
    """Bulk edit form for `ExampleModel` objects."""

    pk = forms.ModelMultipleChoiceField(queryset=ExampleModel.objects.all(), widget=forms.MultipleHiddenInput)
    name = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    number = forms.IntegerField(required=False)

    class Meta:
        nullable_fields = []


class AnotherExampleModelCreateForm(NautobotModelForm):
    """Create only form for `AnotherExampleModel` objects."""

    class Meta:
        model = AnotherExampleModel
        fields = ["name", "number"]


class AnotherExampleModelUpdateForm(NautobotModelForm):
    """Update only form for `AnotherExampleModel` objects."""

    class Meta:
        model = AnotherExampleModel
        fields = ["number", "name"]


class AnotherExampleModelFilterForm(BootstrapMixin, forms.Form):
    """Filtering/search form for `AnotherExampleModel` objects."""

    model = AnotherExampleModel
    q = forms.CharField(required=False, label="Search")
    name = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    number = forms.IntegerField(required=False)


class AnotherExampleModelBulkEditForm(BootstrapMixin, BulkEditForm):
    """Bulk edit form for `ExampleModel` objects."""

    pk = forms.ModelMultipleChoiceField(queryset=AnotherExampleModel.objects.all(), widget=forms.MultipleHiddenInput)
    name = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    number = forms.IntegerField(required=False)

    class Meta:
        nullable_fields = []
