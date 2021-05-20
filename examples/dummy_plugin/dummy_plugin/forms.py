from django import forms

from nautobot.utilities.forms import (
    BootstrapMixin,
    BulkEditForm,
    CSVModelChoiceField,
    CSVModelForm,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
)
from nautobot.extras.forms import (
    CustomFieldBulkEditForm,
    CustomFieldFilterForm,
    CustomFieldModelForm,
    CustomFieldModelCSVForm,
    RelationshipModelForm
)

from .models import DummyModel


# class DummyModelForm(BootstrapMixin, CustomFieldModelForm, RelationshipModelForm):
class DummyModelForm(BootstrapMixin, CustomFieldModelForm):
    """Generic create/update form for `DummyModel` objects."""

    class Meta:
        model = DummyModel
        fields = ["name", "number"]


class DummyModelCSVForm(CustomFieldModelCSVForm):
    """Generic CSV bulk import form for `DummyModel` objects."""

    class Meta:
        model = DummyModel
        fields = DummyModel.csv_headers


class DummyModelFilterForm(BootstrapMixin, CustomFieldFilterForm):
    """Filtering/search form for `DummyModel` objects."""

    model = DummyModel
    q = forms.CharField(required=False, label="Search")
    name = forms.CharField(max_length=20, required=False)
    number = forms.IntegerField(required=False)


class DummyModelBulkEditForm(BootstrapMixin, CustomFieldBulkEditForm):
    """Bulk edit/delete form for `DummyModel` objects."""

    pk = forms.ModelMultipleChoiceField(queryset=DummyModel.objects.all(), widget=forms.MultipleHiddenInput)

    class Meta:
        nullable_fields = []
