from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AdminPasswordChangeForm as _AdminPasswordChangeForm,
    AuthenticationForm,
    PasswordChangeForm as DjangoPasswordChangeForm,
    UserChangeForm as DjangoUserChangeForm,
    UserCreationForm as DjangoUserCreationForm,
)
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import format_html
from timezone_field import TimeZoneFormField

from nautobot.core.events import publish_event
from nautobot.core.forms import (
    BootstrapMixin,
    BulkEditForm,
    BulkEditNullBooleanSelect,
    DateTimePicker,
    DynamicModelMultipleChoiceField,
    JSONField,
)
from nautobot.core.forms.constants import BOOLEAN_WITH_BLANK_CHOICES
from nautobot.core.forms.widgets import StaticSelect2
from nautobot.core.utils.config import get_settings_or_config
from nautobot.users.models import User
from nautobot.users.utils import serialize_user_without_config_and_views

from .models import AdminGroup, ObjectPermission, Token


class LoginForm(BootstrapMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["username"].widget.attrs["placeholder"] = ""
        self.fields["password"].widget.attrs["placeholder"] = ""


class PasswordChangeForm(BootstrapMixin, DjangoPasswordChangeForm):
    pass


class GroupFilterForm(BootstrapMixin, forms.Form):
    """Filter form for the Group list view."""

    model = AdminGroup
    q = forms.CharField(required=False, label="Search")
    name = forms.CharField(required=False)
    user = DynamicModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
    )


class GroupForm(BootstrapMixin, forms.ModelForm):
    """Create/update form for an `AdminGroup`."""

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
    def save(self, commit=True):
        # Override `_AdminPasswordChangeForm.save()` to publish admin change user password event
        instance = super().save(commit)
        if commit:
            payload = serialize_user_without_config_and_views(instance)
            publish_event(topic="nautobot.admin.user.change_password", payload=payload)
        return instance


class ObjectPermissionForm(BootstrapMixin, forms.ModelForm):
    object_types = DynamicModelMultipleChoiceField(
        queryset=ContentType.objects.all(),
        required=True,
    )
    users = DynamicModelMultipleChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
    )
    groups = DynamicModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
    )
    # Canonical CRUD actions presented as checkboxes (mirrors the admin UX).
    can_view = forms.BooleanField(required=False)
    can_add = forms.BooleanField(required=False)
    can_change = forms.BooleanField(required=False)
    can_delete = forms.BooleanField(required=False)
    # `actions` is repurposed for additional/custom actions only.
    actions = JSONField(
        required=False,
        label="Additional actions",
        help_text="Actions granted in addition to those listed above",
    )

    class Meta:
        model = ObjectPermission
        fields = [
            "name",
            "description",
            "enabled",
            "object_types",
            "users",
            "groups",
            "can_view",
            "can_add",
            "can_change",
            "can_delete",
            "actions",
            "constraints",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # When editing, pre-check the boxes for canonical actions, and strip
        # them out of `instance.actions` so they don't also show up in the
        # "Additional actions" widget.
        if self.instance.present_in_database:
            for action in ("view", "add", "change", "delete"):
                if action in self.instance.actions:
                    self.fields[f"can_{action}"].initial = True
                    self.instance.actions.remove(action)

    def clean(self):
        super().clean()
        if not self.cleaned_data.get("actions"):
            self.cleaned_data["actions"] = []
        for action in ("view", "add", "change", "delete"):
            if self.cleaned_data.get(f"can_{action}") and action not in self.cleaned_data["actions"]:
                self.cleaned_data["actions"].append(action)


class ObjectPermissionBulkEditForm(BootstrapMixin, BulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=ObjectPermission.objects.all(), widget=forms.MultipleHiddenInput)
    enabled = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect)

    class Meta:
        fields = ["enabled"]


class ObjectPermissionFilterForm(BootstrapMixin, forms.Form):
    model = ObjectPermission

    q = forms.CharField(required=False, label="Search")
    name = forms.CharField(required=False)
    enabled = forms.NullBooleanField(required=False)
    object_types = DynamicModelMultipleChoiceField(
        queryset=ContentType.objects.all(),
        required=False,
    )
    users = DynamicModelMultipleChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
    )
    groups = DynamicModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
    )


class UserFilterForm(BootstrapMixin, forms.Form):
    model = User
    q = forms.CharField(required=False, label="Search")
    is_active = forms.NullBooleanField(
        required=False,
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    is_staff = forms.NullBooleanField(
        required=False,
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    groups = DynamicModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
    )


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
            "last_login",
            "date_joined",
        )


class UserBulkEditForm(BootstrapMixin, BulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=User.objects.all(), widget=forms.MultipleHiddenInput())
    groups = DynamicModelMultipleChoiceField(queryset=Group.objects.all(), required=False)
    is_active = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect)
    is_staff = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect)
    is_superuser = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect)

    class Meta:
        nullable_fields = []
