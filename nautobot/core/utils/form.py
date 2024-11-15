from nautobot.core.utils.requests import is_single_choice_field


def serialize_query_dict_for_form(query_dict, form):
    data = {}
    for field_name in query_dict:
        field = form.fields.get(field_name)
        if not field:
            continue
        is_multi_choice_field = hasattr(field, "choices")
        data[field_name] = query_dict.getlist(field_name) if is_multi_choice_field else query_dict.get(field_name)
    return data


def serialize_query_dict_for_filterset(query_dict, filterset):
    data = {}
    for field_name in query_dict:
        field = filterset.filters.get(field_name)
        if not field:
            continue
        is_single_choice = is_single_choice_field(filterset, field_name)
        data[field_name] = query_dict.get(field_name) if is_single_choice else query_dict.getlist(field_name)
    return data
