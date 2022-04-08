from django import forms

from nautobot.utilities.forms import (
    BootstrapMixin,
    BulkEditForm,
    CSVModelForm,
)

from example_plugin.models import ExampleModel


class ExamplePluginConfigForm(BootstrapMixin, forms.Form):
    """Example of what a plugin-specific configuration form might look like."""

    magic_word = forms.CharField()
    maximum_velocity = forms.IntegerField(help_text="Meters per second")


class ExampleModelForm(BootstrapMixin, forms.ModelForm):
    """Generic create/update form for `ExampleModel` objects."""

    class Meta:
        model = ExampleModel
        fields = ["name", "number"]


class ExampleModelCSVForm(CSVModelForm):
    """Generic CSV bulk import form for `ExampleModel` objects."""

    class Meta:
        model = ExampleModel
        fields = ExampleModel.csv_headers


class ExampleModelFilterForm(BootstrapMixin, forms.Form):
    """Filtering/search form for `ExampleModel` objects."""

    model = ExampleModel
    q = forms.CharField(required=False, label="Search")
    name = forms.CharField(max_length=20, required=False)
    number = forms.IntegerField(required=False)


class ExampleModelBulkEditForm(BootstrapMixin, BulkEditForm):
    """Bulk edit form for `ExampleModel` objects."""

    pk = forms.ModelMultipleChoiceField(queryset=ExampleModel.objects.all(), widget=forms.MultipleHiddenInput)
    name = forms.CharField(max_length=20, required=False)
    number = forms.IntegerField(required=False)

    class Meta:
        nullable_fields = []
