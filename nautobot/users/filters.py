import django_filters
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from nautobot.users.models import ObjectPermission, Token
from nautobot.utilities.filters import BaseFilterSet, NaturalKeyOrPKMultipleChoiceFilter, SearchFilter

from nautobot.utilities.filters import (BaseFilterSet,
                                        SearchFilter,
                                        RelatedMembershipBooleanFilter,
                                        NaturalKeyOrPKMultipleChoiceFilter)
from nautobot.dcim.models import (
    RackReservation,
    RackRole,
)
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
            # "social_auth":"icontains",
        },
    )
    group_id = django_filters.ModelMultipleChoiceFilter(
        field_name="groups",
        queryset=Group.objects.all(),
        label="Group (ID)",
    )
    # TODO(timizuo): Migrate ModelMultipleChoiceFilter to NaturalKeyOrPKMultipleChoiceFilter: As of now NaturalKeyOrPKMultipleChoiceFilter isn't correctly handling integer id field
    group = django_filters.ModelMultipleChoiceFilter(
        field_name="groups__name",
        queryset=Group.objects.all(),
        to_field_name="name",
        label="Group (name)",
    )
    has_changes = RelatedMembershipBooleanFilter(
        field_name="changes",
        label="Has changes",
    )
    rack_reservations = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="rackreservation_set",
        to_field_name="rack_reservations",
        queryset=RackReservation.objects.all(),
        label="Rack Reservations",
    )
    has_rack_reservations = RelatedMembershipBooleanFilter(
        field_name = "has_rack_reservations",
        label = "Has Rack Reservations"
    )
    has_social_auth = RelatedMembershipBooleanFilter(
        field_name="social_auth",
        label="Has social auth",
    )
    has_tokens = RelatedMembershipBooleanFilter(
        field_name="tokens",
        label="Has token",
    )
    has_object_permissions = RelatedMembershipBooleanFilter(
        field_name="object_permissions",
        label="Has Object Permissions",
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
            "config_data",
            "changes",
            "has_changes",
            # "logentry_set",
            # "has_logentry_set",
            "object_permissions",
            "has_object_permissions",
            # "rackreservation_set",
            # "has_rack_reservations",
            "social_auth",
            "has_social_auth",
            "tokens",
            "has_tokens"
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
        label="User (ID) - Deprecated (use user filter)",
    )
    user = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="users",
        queryset=get_user_model().objects.all(),
        to_field_name="username",
        label="User (ID or username)",
    )
    group_id = django_filters.ModelMultipleChoiceFilter(
        field_name="groups",
        queryset=Group.objects.all(),
        label="Group (ID)",
    )
    # TODO(timizuo): Migrate ModelMultipleChoiceFilter to NaturalKeyOrPKMultipleChoiceFilter
    group = django_filters.ModelMultipleChoiceFilter(
        field_name="groups__name",
        queryset=Group.objects.all(),
        to_field_name="name",
        label="Group (name)",
    )

    class Meta:
        model = ObjectPermission
        fields = ["id", "name", "enabled", "object_types"]
