from django.apps import apps
from django import forms

from nautobot.core.forms import BootstrapMixin


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


def search_model_choices():
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
