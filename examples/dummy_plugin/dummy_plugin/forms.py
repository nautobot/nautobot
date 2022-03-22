from django import forms

from nautobot.utilities.forms import (
    BootstrapMixin,
    BulkEditForm,
    CSVModelForm,
)

from dummy_plugin.models import DummyModel


class DummyPluginConfigForm(BootstrapMixin, forms.Form):
    """Example of what a plugin-specific configuration form might look like."""

    magic_word = forms.CharField()
    maximum_velocity = forms.IntegerField(help_text="Meters per second")


class DummyModelForm(BootstrapMixin, forms.ModelForm):
    """Generic create/update form for `DummyModel` objects."""

    class Meta:
        model = DummyModel
        fields = ["name", "number"]


class DummyModelCSVForm(CSVModelForm):
    """Generic CSV bulk import form for `DummyModel` objects."""

    class Meta:
        model = DummyModel
        fields = DummyModel.csv_headers


class DummyModelFilterForm(BootstrapMixin, forms.Form):
    """Filtering/search form for `DummyModel` objects."""

    model = DummyModel
    q = forms.CharField(required=False, label="Search")
    name = forms.CharField(max_length=20, required=False)
    number = forms.IntegerField(required=False)


class DummyModelBulkEditForm(BootstrapMixin, BulkEditForm):
    """Bulk edit form for `DummyModel` objects."""

    pk = forms.ModelMultipleChoiceField(queryset=DummyModel.objects.all(), widget=forms.MultipleHiddenInput)
    name = forms.CharField(max_length=20, required=False)
    number = forms.IntegerField(required=False)

    class Meta:
        nullable_fields = []
