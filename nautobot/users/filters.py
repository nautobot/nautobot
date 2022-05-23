import django_filters
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from nautobot.users.models import ObjectPermission, Token
from nautobot.utilities.filters import BaseFilterSet, SearchFilter

__all__ = (
    "GroupFilterSet",
    "ObjectPermissionFilterSet",
    "UserFilterSet",
)


class GroupFilterSet(BaseFilterSet):
    q = SearchFilter(filter_predicates={"name": "icontains"})

    class Meta:
        model = Group
        fields = ["id", "name"]


class UserFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "username": "icontains",
            "first_name": "icontains",
            "last_name": "icontains",
            "email": "icontains",
        },
    )
    group_id = django_filters.ModelMultipleChoiceFilter(
        field_name="groups",
        queryset=Group.objects.all(),
        label="Group",
    )
    group = django_filters.ModelMultipleChoiceFilter(
        field_name="groups__name",
        queryset=Group.objects.all(),
        to_field_name="name",
        label="Group (name)",
    )

    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_staff",
            "is_active",
        ]


class TokenFilterSet(BaseFilterSet):
    q = SearchFilter(filter_predicates={"description": "icontains"})

    class Meta:
        model = Token
        fields = ["id", "key", "write_enabled", "created", "expires"]


class ObjectPermissionFilterSet(BaseFilterSet):
    user_id = django_filters.ModelMultipleChoiceFilter(
        field_name="users",
        queryset=get_user_model().objects.all(),
        label="User",
    )
    user = django_filters.ModelMultipleChoiceFilter(
        field_name="users__username",
        queryset=get_user_model().objects.all(),
        to_field_name="username",
        label="User (name)",
    )
    group_id = django_filters.ModelMultipleChoiceFilter(
        field_name="groups",
        queryset=Group.objects.all(),
        label="Group",
    )
    group = django_filters.ModelMultipleChoiceFilter(
        field_name="groups__name",
        queryset=Group.objects.all(),
        to_field_name="name",
        label="Group (name)",
    )

    class Meta:
        model = ObjectPermission
        fields = ["id", "name", "enabled", "object_types"]
