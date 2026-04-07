from nautobot.core.models.utils import serialize_object_v2

STAFFED_USER_FIELDS = ("is_staff", "is_superuser")


def user_is_staffed(user):
    return any(getattr(user, field_name, False) for field_name in STAFFED_USER_FIELDS)


def serialize_user_without_config_and_views(user):
    serialized_data = serialize_object_v2(user)
    for key in ["config_data", "default_saved_views"]:
        serialized_data.pop(key, None)
    return {"data": serialized_data}
