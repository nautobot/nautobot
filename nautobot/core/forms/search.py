from django import forms
from django.apps import apps

from nautobot.core.forms import BootstrapMixin


def search_model_choices():
    """
    Get tuples suitable for use as the `choices` of a `ChoiceField`, listing all searchable models, grouped by app.
    """
    choices = [("", "All Objects")]
    for app_config in apps.get_app_configs():
        searchable_models = getattr(app_config, "searchable_models", None)
        if not searchable_models:
            continue
        app_label = app_config.verbose_name
        model_tuples = [
            (modelname, app_config.get_model(modelname)._meta.verbose_name_plural) for modelname in searchable_models
        ]
        choices.append((app_label, model_tuples))
    return choices


class SearchForm(BootstrapMixin, forms.Form):
    q = forms.CharField(label="Search")

    obj_type = forms.ChoiceField(choices=search_model_choices, required=False, label="Type")

    def __init__(self, *args, q_placeholder=None, **kwargs):
        super().__init__(*args, **kwargs)

        if q_placeholder:
            self.fields["q"].widget.attrs["placeholder"] = q_placeholder
