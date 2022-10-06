from django import forms

from nautobot.utilities.forms import BootstrapMixin

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
