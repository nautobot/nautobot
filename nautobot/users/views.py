from http import HTTPStatus
import logging

from django.contrib import messages
from django.contrib.auth import (
    BACKEND_SESSION_KEY,
    login as auth_login,
    logout as auth_logout,
    update_session_auth_hash,
)
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Count
from django.forms import inlineformset_factory
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch, reverse
from django.utils.decorators import method_decorator
from django.utils.encoding import iri_to_uri
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.timezone import get_default_timezone_name
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import View
from rest_framework.decorators import action
from rest_framework.response import Response

from nautobot.core.events import publish_event
from nautobot.core.forms import ConfirmationForm, restrict_form_fields
from nautobot.core.models.querysets import RestrictedQuerySet
from nautobot.core.ui import object_detail
from nautobot.core.ui.breadcrumbs import (
    Breadcrumbs,
    InstanceBreadcrumbItem,
    ViewNameBreadcrumbItem,
)
from nautobot.core.ui.choices import SectionChoices
from nautobot.core.ui.titles import Titles
from nautobot.core.utils.requests import normalize_querydict
from nautobot.core.views.generic import GenericView
from nautobot.users import filters
from nautobot.users.filters import UserFilterSet
from nautobot.users.utils import serialize_user_without_config_and_views

from ..core.views.mixins import (
    GetReturnURLMixin,
    ObjectBulkDestroyViewMixin,
    ObjectBulkUpdateViewMixin,
    ObjectDestroyViewMixin,
    ObjectDetailViewMixin,
    ObjectEditViewMixin,
    ObjectListViewMixin,
)
from .forms import (
    AdminPasswordChangeForm,
    AdvancedProfileSettingsForm,
    GroupFilterForm,
    GroupForm,
    LoginForm,
    NavbarFavoritesAddForm,
    NavbarFavoritesRemoveForm,
    PasswordChangeForm,
    PreferenceProfileSettingsForm,
    TokenForm,
    UserBulkEditForm,
    UserCreateForm,
    UserFilterForm,
    UserUpdateForm,
)
from .models import Token, User
from .tables import GroupTable, ObjectPermissionTable, UserTable

#
# Login/logout
#


class LoginView(View):
    """
    Perform user authentication via the web UI.
    """

    template_name = "login.html"

    @method_decorator(sensitive_post_parameters("password"))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request):
        form = LoginForm(request)

        if request.user.is_authenticated:
            logger = logging.getLogger("nautobot.auth.login")
            return self.redirect_to_next(request, logger)

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "title": "Login",
            },
        )

    def post(self, request):
        logger = logging.getLogger("nautobot.auth.login")
        form = LoginForm(request, data=request.POST)

        if form.is_valid():
            logger.debug("Login form validation was successful")

            # Authenticate user
            user = form.get_user()
            auth_login(request, form.get_user())
            messages.info(request, f"Logged in as {request.user}.")
            payload = serialize_user_without_config_and_views(user)
            publish_event(topic="nautobot.users.user.login", payload=payload)

            return self.redirect_to_next(request, logger)

        else:
            logger.debug("Login form validation failed")

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "title": "Login",
            },
        )

    def redirect_to_next(self, request, logger):
        if request.method == "POST":
            redirect_to = request.POST.get("next", reverse("home"))
        else:
            redirect_to = request.GET.get("next", reverse("home"))

        if redirect_to and not url_has_allowed_host_and_scheme(url=redirect_to, allowed_hosts=request.get_host()):
            logger.warning(f"Ignoring unsafe 'next' URL passed to login form: {redirect_to}")
            redirect_to = reverse("home")

        logger.debug(f"Redirecting user to {redirect_to}")
        return HttpResponseRedirect(iri_to_uri(redirect_to))


# TODO: The LogoutView should inherit from `LoginRequiredMixin` or `GenericView`
#   to prevent unauthenticated users from accessing the logout page.
#   However, using `LoginRequiredMixin` or `GenericView` as-is currently redirects
#   users to the login page with `?next=/logout/`, which is not desired.
class LogoutView(View):
    """
    Deauthenticate a web user.
    """

    def get(self, request):
        # Log out the user
        if request.user.is_authenticated:
            payload = serialize_user_without_config_and_views(request.user)
            publish_event(topic="nautobot.users.user.logout", payload=payload)
        auth_logout(request)
        messages.info(request, "You have logged out.")

        # Delete session key cookie (if set) upon logout
        response = HttpResponseRedirect(reverse("home"))
        response.delete_cookie("session_key")

        return response


#
# User profiles
#


def is_django_auth_user(request):
    return request.session.get(BACKEND_SESSION_KEY, None) == "nautobot.core.authentication.ObjectPermissionBackend"


class ProfileView(GenericView):
    template_name = "users/profile.html"
    view_titles = Titles(titles={"*": "User Profile"})

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                "is_django_auth_user": is_django_auth_user(request),
                "active_tab": "profile",
                "view_titles": self.get_view_titles(),
                "breadcrumbs": self.get_breadcrumbs(),
            },
        )


class UserUIViewSet(
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    ObjectEditViewMixin,
    ObjectDestroyViewMixin,
    ObjectBulkDestroyViewMixin,
    ObjectBulkUpdateViewMixin,
):
    queryset = User.objects.all()
    filterset_class = UserFilterSet
    filterset_form_class = UserFilterForm
    table_class = UserTable
    create_form_class = UserCreateForm
    update_form_class = UserUpdateForm
    bulk_update_form_class = UserBulkEditForm
    action_buttons = ("add", "export")

    object_detail_content = object_detail.ObjectDetailContent(
        panels=[
            object_detail.ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields=["username", "first_name", "last_name", "email"],
            ),
            object_detail.ObjectFieldsPanel(
                label="Status",
                weight=200,
                section=SectionChoices.LEFT_HALF,
                fields=[
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ],
            ),
            object_detail.ObjectFieldsPanel(
                label="Important Dates",
                weight=300,
                section=SectionChoices.LEFT_HALF,
                fields=[
                    "last_login",
                    "date_joined",
                ],
            ),
            object_detail.ObjectTextPanel(
                label="Config Data",
                section=SectionChoices.RIGHT_HALF,
                weight=100,
                object_field="config_data",
                render_as=object_detail.BaseTextPanel.RenderOptions.JSON,
            ),
            object_detail.ObjectsTablePanel(
                table_title="Groups",
                section=SectionChoices.LEFT_HALF,
                weight=400,
                table_class=GroupTable,
                table_filter="user",
                enable_related_link=False,
            ),
        ]
    )

    @staticmethod
    def get_object_permission_formset_class():
        return inlineformset_factory(
            User,
            User.object_permissions.through,  # pylint: disable=no-member
            fk_name="user",
            fields=("objectpermission",),
            extra=1,
            can_delete=True,
        )

    def get_extra_context(self, request, instance=None):
        context = super().get_extra_context(request, instance)
        if self.action == "update" and instance and "object_permission_formset" not in context:
            formset_class = self.get_object_permission_formset_class()
            context["object_permission_formset"] = formset_class(instance=instance, prefix="object_permissions")
        return context

    def _process_create_or_update_form(self, form):
        request = self.request
        queryset = self.get_queryset()
        with transaction.atomic():
            object_created = not form.instance.present_in_database
            obj = self.form_save(form)
            queryset.get(pk=obj.pk)

            msg = f"{'Created' if object_created else 'Modified'} {queryset.model._meta.verbose_name}"
            self.logger.info(f"{msg} {obj} (PK: {obj.pk})")
            try:
                msg = format_html('{} <a href="{}">{}</a>', msg, obj.get_absolute_url(), obj)
            except AttributeError:
                msg = format_html("{} {}", msg, obj)
            messages.success(request, msg)

            if "_addanother" in request.POST:
                self.success_url = request.get_full_path()
                return

            if "_continue" in request.POST:
                try:
                    self.success_url = reverse("users:user_edit", kwargs={"pk": obj.pk})
                except NoReverseMatch:
                    self.success_url = self.get_return_url(request, obj)
                return

            return_url = form.cleaned_data.get("return_url")
            if url_has_allowed_host_and_scheme(url=return_url, allowed_hosts=request.get_host()):
                self.success_url = iri_to_uri(return_url)
            else:
                self.success_url = self.get_return_url(request, obj)

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="password",
        url_name="password",
        custom_view_base_action="change",
    )
    def password(self, request, pk=None):
        """Reset a user password from the users UI."""
        user_obj = self.get_object()
        form = AdminPasswordChangeForm(user=user_obj, data=request.POST or None)

        if request.method == "POST" and form.is_valid():
            form.save()
            messages.success(request, f"Password updated for {user_obj}.")
            return redirect("users:user_list")

        return Response(
            {
                "obj": user_obj,
                "obj_type": f"{user_obj._meta.verbose_name} password",
                "form": form,
                "editing": True,
                "return_url": reverse("users:user_edit", kwargs={"pk": user_obj.pk}),
            }
        )

    def perform_update(self, request, *args, **kwargs):
        self.obj = self.get_object()
        form_class = self.get_form_class()
        form = form_class(
            data=request.POST,
            files=request.FILES,
            initial=normalize_querydict(request.GET, form_class=form_class),
            instance=self.obj,
        )
        restrict_form_fields(form, request.user)

        formset_class = self.get_object_permission_formset_class()
        object_permission_formset = formset_class(data=request.POST, instance=self.obj, prefix="object_permissions")

        if form.is_valid() and object_permission_formset.is_valid():
            with transaction.atomic():
                response = self.form_valid(form)
                object_permission_formset.save()
            return response

        return Response({"form": form, "object_permission_formset": object_permission_formset})


class UserConfigView(GenericView):
    template_name = "users/preferences.html"
    view_titles = Titles(titles={"*": "User Preferences"})

    def get(self, request):
        initial = {}
        initial["timezone"] = request.user.get_config("timezone", get_default_timezone_name())
        form = PreferenceProfileSettingsForm(initial=initial)
        preferences = request.user.all_config()

        return render(
            request,
            self.template_name,
            {
                "preferences": preferences,
                "form": form,
                "active_tab": "preferences",
                "is_django_auth_user": is_django_auth_user(request),
                "view_titles": self.get_view_titles(),
                "breadcrumbs": self.get_breadcrumbs(),
            },
        )

    def post(self, request):
        is_preference_update_post = "_update_preference_form" in request.POST
        if is_preference_update_post:
            form = PreferenceProfileSettingsForm(request.POST)
            if form.is_valid():
                response = redirect("user:preferences")
                if timezone := form.cleaned_data["timezone"]:
                    request.user.set_config("timezone", str(timezone), commit=True)
                return response

            return render(
                request,
                self.template_name,
                {
                    "preferences": request.user.all_config(),
                    "form": form,
                    "active_tab": "preferences",
                    "is_django_auth_user": is_django_auth_user(request),
                },
            )

        else:
            user = request.user
            data = user.all_config()

            # Delete selected preferences
            for key in request.POST.getlist("pk"):
                if key in data:
                    user.clear_config(key)
            user.save()
            messages.success(request, "Your preferences have been updated.")

            return redirect("user:preferences")


class UserNavbarFavoritesAddView(GetReturnURLMixin, GenericView):
    def post(self, request):
        if request.headers.get("HX-Request", False):
            form = NavbarFavoritesAddForm(request.POST)
            if form.is_valid():
                navbar_favorites = request.user.get_config("navbar_favorites", [])
                navbar_favorites.append(form.cleaned_data)
                navbar_favorites = sorted(navbar_favorites, key=lambda d: d.get("name", ""))
                request.user.set_config("navbar_favorites", navbar_favorites, commit=True)

                return render(
                    request,
                    "inc/nav_menu.html",
                    status=HTTPStatus.CREATED,
                )

        return redirect(self.get_return_url(request))


class UserNavbarFavoritesDeleteView(GetReturnURLMixin, GenericView):
    def post(self, request):
        if request.headers.get("HX-Request", False):
            form = NavbarFavoritesRemoveForm(request.POST)
            if form.is_valid():
                navbar_favorites = request.user.get_config("navbar_favorites", [])
                navbar_favorites = [item for item in navbar_favorites if item.get("link") != form.cleaned_data["link"]]
                request.user.set_config("navbar_favorites", navbar_favorites, commit=True)

                return render(
                    request,
                    "inc/nav_menu.html",
                    status=HTTPStatus.OK,
                )

        return redirect(self.get_return_url(request))


class ChangePasswordView(GenericView):
    template_name = "users/change_password.html"
    view_titles = Titles(titles={"*": "Change Password"})

    RESTRICTED_NOTICE = "Remotely authenticated user credentials cannot be changed within Nautobot."

    def get(self, request):
        # Non-Django authentication users cannot change their password here
        if not is_django_auth_user(request):
            messages.warning(
                request,
                self.RESTRICTED_NOTICE,
            )
            return redirect("user:profile")

        form = PasswordChangeForm(user=request.user)

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "active_tab": "change_password",
                "is_django_auth_user": is_django_auth_user(request),
                "view_titles": self.get_view_titles(),
                "breadcrumbs": self.get_breadcrumbs(),
            },
        )

    def post(self, request):
        # Non-Django authentication users cannot change their password here
        if not is_django_auth_user(request):
            messages.warning(
                request,
                self.RESTRICTED_NOTICE,
            )
            return redirect("user:profile")

        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            messages.success(request, "Your password has been changed successfully.")
            payload = serialize_user_without_config_and_views(request.user)
            publish_event(topic="nautobot.users.user.change_password", payload=payload)
            return redirect("user:profile")

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "active_tab": "change_password",
                "is_django_auth_user": is_django_auth_user(request),
            },
        )


#
# Groups
#


class GroupUIViewSet(
    ObjectDetailViewMixin,
    ObjectListViewMixin,
    ObjectEditViewMixin,
    ObjectDestroyViewMixin,
    ObjectBulkDestroyViewMixin,
):
    queryset = Group.objects.all()
    filterset_class = filters.GroupFilterSet
    filterset_form_class = GroupFilterForm
    create_form_class = GroupForm
    update_form_class = GroupForm
    table_class = GroupTable
    action_buttons = ("add", "export")
    breadcrumbs = Breadcrumbs(
        items={
            "detail": [
                ViewNameBreadcrumbItem(label="Groups", view_name="users:group_list"),
                InstanceBreadcrumbItem(),
            ],
            "create": [
                ViewNameBreadcrumbItem(label="Groups", view_name="users:group_list"),
                ViewNameBreadcrumbItem(label="Add Group", view_name=None),
            ],
            "update": [
                ViewNameBreadcrumbItem(label="Groups", view_name="users:group_list"),
                InstanceBreadcrumbItem(),
            ],
        }
    )

    object_detail_content = object_detail.ObjectDetailContent(
        panels=[
            object_detail.ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields="__all__",
            ),
            object_detail.ObjectsTablePanel(
                table_title="Permissions",
                section=SectionChoices.FULL_WIDTH,
                weight=200,
                table_class=ObjectPermissionTable,
                table_filter="groups",
                enable_related_link=False,
                show_table_config_button=False,
            ),
        ],
    )

    @staticmethod
    def get_object_permission_formset_class():
        return inlineformset_factory(
            Group,
            Group.object_permissions.through,  # pylint: disable=no-member
            fk_name="group",
            fields=("objectpermission",),
            extra=1,
            can_delete=True,
        )

    def get_template_name(self):
        if self.action in ("create", "update"):
            return f"users/group_{self.action}.html"
        return super().get_template_name()

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.annotate(user_count=Count("user"))

    def get_extra_context(self, request, instance=None):
        context = super().get_extra_context(request, instance)
        if self.action in ("create", "update") and "object_permission_formset" not in context:
            formset_class = self.get_object_permission_formset_class()
            if request.method == "POST":
                context["object_permission_formset"] = formset_class(
                    data=request.POST,
                    instance=instance or self.get_object(),
                    prefix="object_permissions",
                )
            else:
                context["object_permission_formset"] = formset_class(
                    instance=instance or self.get_object(),
                    prefix="object_permissions",
                )
        return context

    def perform_create(self, request, *args, **kwargs):
        self.obj = self.get_object()
        form_class = self.get_form_class()
        form = form_class(
            data=request.POST,
            files=request.FILES,
            initial=normalize_querydict(request.GET, form_class=form_class),
            instance=self.obj,
        )
        restrict_form_fields(form, request.user)
        formset_class = self.get_object_permission_formset_class()
        object_permission_formset = formset_class(data=request.POST, instance=self.obj, prefix="object_permissions")
        if form.is_valid() and object_permission_formset.is_valid():
            with transaction.atomic():
                response = self.form_valid(form)
                if not getattr(self, "has_error", False):
                    object_permission_formset.instance = form.instance
                    object_permission_formset.save()
            return response
        return Response({"form": form, "object_permission_formset": object_permission_formset})

    def perform_update(self, request, *args, **kwargs):
        self.obj = self.get_object()
        form_class = self.get_form_class()
        form = form_class(
            data=request.POST,
            files=request.FILES,
            initial=normalize_querydict(request.GET, form_class=form_class),
            instance=self.obj,
        )
        restrict_form_fields(form, request.user)
        formset_class = self.get_object_permission_formset_class()
        object_permission_formset = formset_class(data=request.POST, instance=self.obj, prefix="object_permissions")
        if form.is_valid() and object_permission_formset.is_valid():
            with transaction.atomic():
                response = self.form_valid(form)
                object_permission_formset.save()
            return response
        return Response({"form": form, "object_permission_formset": object_permission_formset})


#
# API tokens
#


class TokenListView(GenericView):
    view_titles = Titles(titles={"*": "API Tokens"})

    def get(self, request):
        tokens = Token.objects.filter(user=request.user)

        return render(
            request,
            "users/api_tokens.html",
            {
                "tokens": tokens,
                "active_tab": "api_tokens",
                "is_django_auth_user": is_django_auth_user(request),
                "view_titles": self.get_view_titles(),
                "breadcrumbs": self.get_breadcrumbs(),
            },
        )


class TokenEditView(GenericView):
    def get(self, request, pk=None):
        if pk is not None:
            if not request.user.has_perm("users.change_token"):
                return HttpResponseForbidden()
            token = get_object_or_404(Token.objects.filter(user=request.user), pk=pk)
        else:
            if not request.user.has_perm("users.add_token"):
                return HttpResponseForbidden()
            token = Token(user=request.user)

        form = TokenForm(instance=token)

        return render(
            request,
            "generic/object_create.html",
            {
                "obj": token,
                "obj_type": token._meta.verbose_name,
                "form": form,
                "return_url": reverse("user:token_list"),
                "editing": token.present_in_database,
            },
        )

    def post(self, request, pk=None):
        if pk is not None:
            token = get_object_or_404(Token.objects.filter(user=request.user), pk=pk)
            form = TokenForm(request.POST, instance=token)
        else:
            token = Token()
            form = TokenForm(request.POST)

        if form.is_valid():
            token = form.save(commit=False)
            token.user = request.user
            token.save()

            msg = f"Modified token {token}" if pk else f"Created token {token}"
            messages.success(request, msg)

            if "_addanother" in request.POST:
                return redirect(request.path)
            else:
                return redirect("user:token_list")

        return render(
            request,
            "generic/object_create.html",
            {
                "obj": token,
                "obj_type": token._meta.verbose_name,
                "form": form,
                "return_url": reverse("user:token_list"),
                "editing": token.present_in_database,
            },
        )


class TokenDeleteView(GenericView):
    def get(self, request, pk):
        token = get_object_or_404(Token.objects.filter(user=request.user), pk=pk)
        initial_data = {
            "return_url": reverse("user:token_list"),
        }
        form = ConfirmationForm(initial=initial_data)

        return render(
            request,
            "generic/object_destroy.html",
            {
                "obj": token,
                "obj_type": token._meta.verbose_name,
                "form": form,
                "return_url": reverse("user:token_list"),
            },
        )

    def post(self, request, pk):
        token = get_object_or_404(Token.objects.filter(user=request.user), pk=pk)
        form = ConfirmationForm(request.POST)
        if form.is_valid():
            token.delete()
            messages.success(request, "Token deleted")
            return redirect("user:token_list")

        return render(
            request,
            "generic/object_destroy.html",
            {
                "obj": token,
                "obj_type": token._meta.verbose_name,
                "form": form,
                "return_url": reverse("user:token_list"),
            },
        )


#
# Advanced Profile Settings
#


class AdvancedProfileSettingsEditView(GenericView):
    template_name = "users/advanced_settings_edit.html"
    view_titles = Titles(titles={"*": "Advanced Settings"})

    def get(self, request):
        silk_record_requests = request.session.get("silk_record_requests", False)
        form = AdvancedProfileSettingsForm(initial={"request_profiling": silk_record_requests})

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "active_tab": "advanced_settings",
                "return_url": reverse("user:advanced_settings_edit"),
                "is_django_auth_user": is_django_auth_user(request),
                "view_titles": self.get_view_titles(),
                "breadcrumbs": self.get_breadcrumbs(),
            },
        )

    def post(self, request):
        form = AdvancedProfileSettingsForm(request.POST)

        if form.is_valid():
            silk_record_requests = form.cleaned_data["request_profiling"]

            # Set the value for `silk_record_requests` in the session
            request.session["silk_record_requests"] = silk_record_requests

            if silk_record_requests:
                msg = "Enabled request profiling for the duration of the login session."
            else:
                msg = "Disabled request profiling."
            messages.success(request, msg)

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "active_tab": "advanced_settings",
                "return_url": reverse("user:advanced_settings_edit"),
                "is_django_auth_user": is_django_auth_user(request),
            },
        )
