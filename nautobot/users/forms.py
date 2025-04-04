from django import forms
from django.contrib.auth.forms import (
    AdminPasswordChangeForm as _AdminPasswordChangeForm,
    AuthenticationForm,
    PasswordChangeForm as DjangoPasswordChangeForm,
)
from timezone_field import TimeZoneFormField

from nautobot.core.events import publish_event
from nautobot.core.forms import BootstrapMixin, DateTimePicker
from nautobot.core.forms.widgets import StaticSelect2
from nautobot.core.utils.config import get_settings_or_config
from nautobot.users.utils import serialize_user_without_config_and_views

from .models import Token


class LoginForm(BootstrapMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["username"].widget.attrs["placeholder"] = ""
        self.fields["password"].widget.attrs["placeholder"] = ""


class PasswordChangeForm(BootstrapMixin, DjangoPasswordChangeForm):
    pass


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


class PreferenceProfileSettingsForm(BootstrapMixin, forms.Form):
    timezone = TimeZoneFormField(required=False, help_text="Set your default timezone", widget=StaticSelect2)


class AdminPasswordChangeForm(_AdminPasswordChangeForm):
    def save(self, commit=True):
        # Override `_AdminPasswordChangeForm.save()` to publish admin change user password event
        instance = super().save(commit)
        if commit:
            payload = serialize_user_without_config_and_views(instance)
            publish_event(topic="nautobot.admin.user.change_password", payload=payload)
        return instance
