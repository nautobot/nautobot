from django import forms

from nautobot.ipam import formfields


class AddressFieldMixin(forms.ModelForm):
    """
    ModelForm mixin for IPAddress based models.
    """

    address = formfields.IPNetworkFormField()

    def __init__(self, *args, **kwargs):

        instance = kwargs.get("instance")
        initial = kwargs.get("initial", {}).copy()

        # If initial already has an `address`, we want to use that `address` as it was passed into
        # the form. If we're editing an object with a `address` field, we need to patch initial
        # to include `address` because it is a computed field.
        if "address" not in initial and instance is not None:
            initial["address"] = instance.address

        kwargs["initial"] = initial

        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()

        # Need to set instance attribute for `address` to run proper validation on Model.clean()
        self.instance.address = self.cleaned_data.get("address")


class PrefixFieldMixin(forms.ModelForm):
    """
    ModelForm mixin for IPNetwork based models.
    """

    prefix = formfields.IPNetworkFormField()

    def __init__(self, *args, **kwargs):

        instance = kwargs.get("instance")
        initial = kwargs.get("initial", {}).copy()

        # If initial already has a `prefix`, we want to use that `prefix` as it was passed into
        # the form. If we're editing an object with a `prefix` field, we need to patch initial
        # to include `prefix` because it is a computed field.
        if "prefix" not in initial and instance is not None:
            initial["prefix"] = instance.prefix

        kwargs["initial"] = initial

        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()

        # Need to set instance attribute for `prefix` to run proper validation on Model.clean()
        self.instance.prefix = self.cleaned_data.get("prefix")
