from django import forms
from django.contrib.auth.forms import (
    AdminPasswordChangeForm as _AdminPasswordChangeForm,
    AuthenticationForm,
    PasswordChangeForm as DjangoPasswordChangeForm,
    UserChangeForm as DjangoUserChangeForm,
    UserCreationForm as DjangoUserCreationForm,
)
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import format_html
from timezone_field import TimeZoneFormField

from nautobot.core.events import publish_event
from nautobot.core.forms import BootstrapMixin, BulkEditForm, BulkEditNullBooleanSelect, DateTimePicker
from nautobot.core.forms.widgets import StaticSelect2, StaticSelect2Multiple
from nautobot.core.utils.config import get_settings_or_config
from nautobot.users.models import User
from nautobot.users.utils import serialize_user_without_config_and_views

from .models import AdminGroup, Token


class LoginForm(BootstrapMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["username"].widget.attrs["placeholder"] = ""
        self.fields["password"].widget.attrs["placeholder"] = ""


class PasswordChangeForm(BootstrapMixin, DjangoPasswordChangeForm):
    pass


class GroupFilterForm(BootstrapMixin, forms.Form):
    model = AdminGroup
    q = forms.CharField(required=False, label="Search")
    name = forms.CharField(required=False)


class GroupForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = AdminGroup
        fields = ["name"]


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
    timezone = TimeZoneFormField(required=False, help_text="Set your preferred timezone.", widget=StaticSelect2)


class NavbarFavoritesAddForm(forms.Form):
    link = forms.CharField()
    name = forms.CharField()
    tab_name = forms.CharField()


class NavbarFavoritesRemoveForm(forms.Form):
    link = forms.CharField()


class AdminPasswordChangeForm(_AdminPasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "usable_password" in self.fields and self.user is not None and not self.is_bound:
            self.initial["usable_password"] = self.user.has_usable_password()

    def save(self, commit=True):
        # Override `_AdminPasswordChangeForm.save()` to publish admin change user password event
        instance = super().save(commit)
        if commit:
            payload = serialize_user_without_config_and_views(instance)
            publish_event(topic="nautobot.admin.user.change_password", payload=payload)
        return instance


class UserFilterForm(BootstrapMixin, forms.Form):
    model = User
    q = forms.CharField(required=False, label="Search")


class UserCreateForm(BootstrapMixin, DjangoUserCreationForm):
    usable_password = forms.TypedChoiceField(
        label="Password-based authentication",
        choices=((True, "Enabled"), (False, "Disabled")),
        coerce=lambda value: value in (True, "True", "true", "1", 1),
        initial=True,
        required=True,
        widget=forms.RadioSelect,
        help_text=(
            "Whether the user will be able to authenticate using a password or not. "
            "If disabled, they may still be able to authenticate using other backends, "
            "such as Single Sign-On or LDAP."
        ),
    )

    class Meta(DjangoUserCreationForm.Meta):
        model = User
        fields = ("username",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].required = False
        self.fields["password2"].required = False

    def clean(self):
        cleaned_data = super().clean()
        usable_password = cleaned_data.get("usable_password", True)
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if usable_password:
            if not password1 or not password2:
                raise ValidationError("Password and password confirmation are required when password login is enabled.")
            if password1 != password2:
                raise ValidationError("The two password fields didn't match.")
        else:
            cleaned_data["password1"] = ""
            cleaned_data["password2"] = ""
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        if not self.cleaned_data.get("usable_password", True):
            user.set_unusable_password()
        if commit:
            user.save()
        return user


class UserUpdateForm(BootstrapMixin, DjangoUserChangeForm):
    last_login = forms.DateTimeField(required=False, widget=DateTimePicker())
    date_joined = forms.DateTimeField(required=False, widget=DateTimePicker())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and "password" in self.fields:
            reset_url = reverse("users:user_password", kwargs={"pk": self.instance.pk})
            self.fields["password"].help_text = format_html(
                'Raw passwords are not stored, so there is no way to see this user\'s password. <a href="{}">Reset password</a>',
                reset_url,
            )

    class Meta(DjangoUserChangeForm.Meta):
        model = User
        fields = (
            "username",
            "password",
            "first_name",
            "last_name",
            "email",
            "groups",
            "is_active",
            "is_staff",
            "is_superuser",
            "user_permissions",
            "last_login",
            "date_joined",
        )


class UserBulkEditForm(BootstrapMixin, BulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=User.objects.all(), widget=forms.MultipleHiddenInput())
    groups = forms.ModelMultipleChoiceField(queryset=Group.objects.all(), required=False, widget=StaticSelect2Multiple)
    is_active = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect)
    is_staff = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect)
    is_superuser = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect)

    class Meta:
        nullable_fields = []
