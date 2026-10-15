from django import forms
from django.contrib.contenttypes.models import ContentType

from nautobot.core.forms import DynamicModelChoiceField, DynamicModelMultipleChoiceField
from nautobot.core.utils.config import get_settings_or_config
from nautobot.dcim.models import Location
from nautobot.ipam.models import IPAddress


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


class UnassignedPrimaryIPFormMixin(forms.Form):
    """
    Mixin for Device, VirtualMachine, and VirtualDeviceContext forms to select a primary IP address that isn't
    assigned to any interface, as permitted when `PRIMARY_IP_REQUIRES_INTERFACE_ASSIGNMENT` is disabled.

    A selection in `unassigned_primary_ip4`/`unassigned_primary_ip6` is applied to `primary_ip4`/`primary_ip6`.
    """

    unassigned_primary_ip4 = DynamicModelChoiceField(
        queryset=IPAddress.objects.all(),
        required=False,
        query_params={"ip_version": 4, "has_interface_assignments": False},
        label="Unassigned primary IPv4",
        help_text="An IPv4 address that is not assigned to any interface",
    )
    unassigned_primary_ip6 = DynamicModelChoiceField(
        queryset=IPAddress.objects.all(),
        required=False,
        query_params={"ip_version": 6, "has_interface_assignments": False},
        label="Unassigned primary IPv6",
        help_text="An IPv6 address that is not assigned to any interface",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        require_assignment = get_settings_or_config("PRIMARY_IP_REQUIRES_INTERFACE_ASSIGNMENT")
        for field_name in ["primary_ip4", "primary_ip6"]:
            current_ip = getattr(self.instance, field_name)
            if current_ip is not None and not self._is_interface_primary_ip(current_ip):
                # Present the current unassigned primary IP here, so that it isn't lost when the form is resubmitted
                self.initial[f"unassigned_{field_name}"] = current_ip.pk
                self.initial[field_name] = None
                if require_assignment:
                    # It may be retained or cleared, but no other unassigned IP may be selected
                    unassigned_field = self.fields[f"unassigned_{field_name}"]
                    unassigned_field.queryset = IPAddress.objects.filter(pk=current_ip.pk)
                    unassigned_field.widget.add_query_param("id", str(current_ip.pk))
                    unassigned_field.help_text = (
                        "This IP address is not assigned to any of this object's interfaces. "
                        "It can be retained or cleared, but not replaced with another unassigned IP address."
                    )
            elif require_assignment:
                del self.fields[f"unassigned_{field_name}"]

    def _is_interface_primary_ip(self, ip):
        """Whether `ip` is a primary IP choice by way of this object's interfaces, directly or as a NAT outside IP."""
        host_assignments = self.instance.get_interface_assignments_filter()
        if ip.interface_assignments.filter(host_assignments).exists():
            return True
        return ip.nat_inside is not None and ip.nat_inside.interface_assignments.filter(host_assignments).exists()

    def clean(self):
        super().clean()
        for field_name in ["primary_ip4", "primary_ip6"]:
            unassigned_ip = self.cleaned_data.get(f"unassigned_{field_name}")
            if unassigned_ip is None:
                continue
            if self.cleaned_data.get(field_name) not in (None, unassigned_ip):
                self.add_error(
                    f"unassigned_{field_name}",
                    f"Cannot select both an unassigned primary IP and an interface primary IP ({self.cleaned_data[field_name]}).",
                )
            else:
                self.cleaned_data[field_name] = unassigned_ip
        return self.cleaned_data


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
