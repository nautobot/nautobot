from logging import getLogger

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from nautobot.extras.models import CustomField
from nautobot.extras.utils import FeatureQuery

logger = getLogger("nautobot.extras.cfcleanup")

class Command(BaseCommand):
    help = "Reset custom field attachments"

    @transaction.atomic
    def delete_custom_field_data(self, field_name, content_type_pk_set):
        """
        Delete the values for a custom field

        Args:
            field_name (str): The name of the custom field which is being deleted
            content_type_pk_set (list): List of PKs for content types to act upon
        """
        for ct in ContentType.objects.filter(pk__in=content_type_pk_set):
            model = ct.model_class()
            logger.info(f"Removing Custom Field {field_name} from {model.__name__}")
            for obj in model.objects.filter(**{f"_custom_field_data__{field_name}__isnull": False}):
                del obj._custom_field_data[field_name]
                obj.save()


    @transaction.atomic
    def provision_field(self, field, content_type_pk_set):
        """
        Provision a new custom field on all relevant content type object instances.

        Args:
            field (CustomField): The custom field being provisioned
            content_type_pk_set (list): List of PKs for content types to act upon
        """
        for ct in ContentType.objects.filter(pk__in=content_type_pk_set):
            model = ct.model_class()
            logger.info(f"Provisioning Field {field.name} for {model.__name__}")
            for obj in model.objects.all():
                obj._custom_field_data[field.name] = field.default
                obj.save()


    def handle(self, *args, **kwargs):
        """Run through all custom fields and ensure they are associated with the correct content types."""
        # The list of all content type pks which can have custom fields
        all_content_type_pks = [ ct.pk for ct in ContentType.objects.filter(FeatureQuery("custom_fields").get_query()) ]
        for custom_field in CustomField.objects.all():
            # The list of all content_types for which this custom field should be associated with
            cf_content_type_pks = [ ct.pk for ct in custom_field.content_types.all() ]
            # The list of all content_types for which this custom field should NOT be associated with
            content_type_pks_to_remove = list(set(all_content_type_pks)-set(cf_content_type_pks))
            # Remove any custom field data which should not exist
            self.delete_custom_field_data(custom_field.name, content_type_pks_to_remove)
            # Add the custom field to any content type for which it should exist
            self.provision_field(custom_field, cf_content_type_pks)
