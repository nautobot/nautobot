from django import forms

from nautobot.apps.forms import BulkEditForm, CSVModelForm, NautobotModelForm
from nautobot.utilities.forms import BootstrapMixin

from example_plugin.models import AnotherExampleModel, ExampleModel, ValueModel, ClassificationGroupsModel


class ExamplePluginConfigForm(BootstrapMixin, forms.Form):
    """Example of what a plugin-specific configuration form might look like."""

    magic_word = forms.CharField()
    maximum_velocity = forms.IntegerField(help_text="Meters per second")


class ExampleModelForm(NautobotModelForm):
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


class AnotherExampleModelForm(NautobotModelForm):
    """Generic create/update form for `AnotherExampleModel` objects."""

    class Meta:
        model = AnotherExampleModel
        fields = ["name", "number"]


class AnotherExampleModelFilterForm(BootstrapMixin, forms.Form):
    """Filtering/search form for `AnotherExampleModel` objects."""

    model = AnotherExampleModel
    q = forms.CharField(required=False, label="Search")
    name = forms.CharField(max_length=20, required=False)
    number = forms.IntegerField(required=False)


class AnotherExampleModelBulkEditForm(BootstrapMixin, BulkEditForm):
    """Bulk edit form for `ExampleModel` objects."""

    pk = forms.ModelMultipleChoiceField(queryset=AnotherExampleModel.objects.all(), widget=forms.MultipleHiddenInput)
    name = forms.CharField(max_length=20, required=False)
    number = forms.IntegerField(required=False)

    class Meta:
        nullable_fields = []


# Value Model


class ValueModelForm(NautobotModelForm):
    """Generic create/update form for `ValueModel` objects."""

    class Meta:
        model = ValueModel
        fields = ["name", "value", "value_type"]


class ValueModelCSVForm(CSVModelForm):
    """Generic CSV bulk import form for `ValueModel` objects."""

    class Meta:
        model = ValueModel
        fields = ValueModel.csv_headers


class ValueModelFilterForm(BootstrapMixin, forms.Form):
    """Filtering/search form for `ValueModel` objects."""

    model = ValueModel
    q = forms.CharField(required=False, label="Search")
    name = forms.CharField(max_length=20, required=False)


class ValueModelBulkEditForm(BootstrapMixin, BulkEditForm):
    """Bulk edit form for `ValueModel` objects."""

    pk = forms.ModelMultipleChoiceField(queryset=ValueModel.objects.all(), widget=forms.MultipleHiddenInput)
    name = forms.CharField(max_length=20, required=False)

    class Meta:
        nullable_fields = []


# Classification Model


class ClassificationGroupsModelForm(NautobotModelForm):
    """Generic create/update form for `ClassificationGroupsModel` objects."""

    class Meta:
        model = ClassificationGroupsModel
        fields = ["name", "asset_tag", "network", "environment"]


class ClassificationGroupsModelCSVForm(CSVModelForm):
    """Generic CSV bulk import form for `ClassificationGroupsModel` objects."""

    class Meta:
        model = ClassificationGroupsModel
        fields = ClassificationGroupsModel.csv_headers


class ClassificationGroupsModelFilterForm(BootstrapMixin, forms.Form):
    """Filtering/search form for `ClassificationGroupsModel` objects."""

    model = ClassificationGroupsModel
    q = forms.CharField(required=False, label="Search")
    name = forms.CharField(max_length=20, required=False)


class ClassificationGroupsModelBulkEditForm(BootstrapMixin, BulkEditForm):
    """Bulk edit form for `ClassificationGroupsModel` objects."""

    pk = forms.ModelMultipleChoiceField(
        queryset=ClassificationGroupsModel.objects.all(), widget=forms.MultipleHiddenInput
    )
    name = forms.CharField(max_length=20, required=False)

    class Meta:
        nullable_fields = []
