from logging import getLogger

from django.contrib.contenttypes.models import ContentType
from django_rq import job

from nautobot.extras.choices import CustomFieldTypeChoices

logger = getLogger("nautobot.extras.tasks")


@job("custom_fields")
def update_custom_field_choice_data(field_id, old_value, new_value):
    """
    Update the values for a custom field choice used in objects' _custom_field_data for the given field.

    Args:
        field_id (uuid4): The PK of the custom field to which this choice value relates
        old_value (str): The existing value of the choice
        new_value (str): The value which will be used as replacement
    """
    from nautobot.extras.models import CustomField

    try:
        field = CustomField.objects.get(pk=field_id)
    except CustomField.DoesNotExist:
        logger.error(f"Custom field with ID {field_id} not found, failing to act on choice data.")
        return False

    if field.type == CustomFieldTypeChoices.TYPE_SELECT:
        # Loop through all field content types and search for values to update
        for ct in field.content_types.all():
            model = ct.model_class()
            for obj in model.objects.filter(**{f"_custom_field_data__{field.name}": old_value}):
                obj._custom_field_data[field.name] = new_value
                obj.save()

    elif field.type == CustomFieldTypeChoices.TYPE_MULTISELECT:
        # Loop through all field content types and search for values to update
        for ct in field.content_types.all():
            model = ct.model_class()
            for obj in model.objects.filter(**{f"_custom_field_data__{field.name}__contains": old_value}):
                old_list = obj._custom_field_data[field.name]
                new_list = [new_value if e == old_value else e for e in old_list]
                obj._custom_field_data[field.name] = new_list
                obj.save()

    else:
        logger.error(f"Unknown field type, failing to act on choice data for this field {field.name}.")
        return False


@job("custom_fields")
def delete_custom_field_data(field_name, content_type_pk_set):
    """
    Delete the values for a custom field

    Args:
        field_name (str): The name of the custom field which is being deleted
        content_type_pk_set (list): List of PKs for content types to act upon
    """
    for ct in ContentType.objects.filter(pk__in=content_type_pk_set):
        model = ct.model_class()
        for obj in model.objects.filter(**{f"_custom_field_data__{field_name}__isnull": False}):
            del obj._custom_field_data[field_name]
            obj.save()


@job("custom_fields")
def provision_field(field_id, content_type_pk_set):
    """
    Provision a new custom field on all relevant content type object instances.

    Args:
        field_id (uuid4): The PK of the custom field being provisioned
        content_type_pk_set (list): List of PKs for content types to act upon
    """
    from nautobot.extras.models import CustomField

    try:
        field = CustomField.objects.get(pk=field_id)
    except CustomField.DoesNotExist:
        logger.error(f"Custom field with ID {field_id} not found, failing to provision.")
        return False

    for ct in ContentType.objects.filter(pk__in=content_type_pk_set):
        model = ct.model_class()
        for obj in model.objects.all():
            obj._custom_field_data[field.name] = field.default
            obj.save()
