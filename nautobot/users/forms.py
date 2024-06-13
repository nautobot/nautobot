from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm as DjangoPasswordChangeForm,
)

from nautobot.core.forms import BootstrapMixin, DateTimePicker
from nautobot.core.utils.config import get_settings_or_config

from .models import SavedView, Token


class LoginForm(BootstrapMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["username"].widget.attrs["placeholder"] = ""
        self.fields["password"].widget.attrs["placeholder"] = ""


class PasswordChangeForm(BootstrapMixin, DjangoPasswordChangeForm):
    pass


class SavedViewForm(BootstrapMixin, forms.ModelForm):
    is_global_default = forms.BooleanField(
        label="Is global default",
        required=False,
        help_text="If checked, this saved view will be used globally as the default saved view for this particular view",
    )
    is_shared = forms.BooleanField(
        label="Is shared",
        required=False,
        help_text="If checked, all users will be able to see this saved view",
    )

    class Meta:
        model = SavedView
        fields = ["name", "is_global_default", "is_shared"]


class SavedViewModalForm(BootstrapMixin, forms.ModelForm):
    is_shared = forms.BooleanField(
        label="Is shared",
        required=False,
        help_text="If checked, all users will be able to see this saved view",
    )

    class Meta:
        model = SavedView
        fields = ["name", "config", "is_shared"]


class TokenForm(BootstrapMixin, forms.ModelForm):
    key = forms.CharField(
        required=False,
        help_text="If no key is provided, one will be generated automatically.",
    )

    class Meta:
        model = Token
        fields = [
            "key",
            "write_enabled",
            "expires",
            "description",
        ]
        widgets = {
            "expires": DateTimePicker(),
        }


class AdvancedProfileSettingsForm(BootstrapMixin, forms.Form):
    request_profiling = forms.BooleanField(
        required=False,
        help_text="Enable request profiling for the duration of the login session. "
        "This is for debugging purposes and should only be enabled when "
        "instructed by an administrator.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ALLOW_REQUEST_PROFILING is a constance config option that controls whether users can enable request profiling
        ALLOW_REQUEST_PROFILING = get_settings_or_config("ALLOW_REQUEST_PROFILING")
        if not ALLOW_REQUEST_PROFILING:
            self.fields["request_profiling"].disabled = True

    def clean(self):
        # ALLOW_REQUEST_PROFILING is a constance config option that controls whether users can enable request profiling
        ALLOW_REQUEST_PROFILING = get_settings_or_config("ALLOW_REQUEST_PROFILING")
        if not ALLOW_REQUEST_PROFILING and self.cleaned_data["request_profiling"]:
            raise forms.ValidationError(
                {"request_profiling": "Request profiling has been globally disabled by an administrator."}
            )
