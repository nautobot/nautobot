from nautobot.core.models.utils import serialize_object_v2


def serialize_user_without_config_and_views(user):
    serialized_data = serialize_object_v2(user)
    for key in ["config_data", "default_saved_views"]:
        serialized_data.pop(key, None)
    return {"data": serialized_data}
