from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction

from nautobot.extras.utils import FeatureQuery


class Command(BaseCommand):
    help = "Adds/Removes any custom fields which should or should not exist on an object. This command should not be run unless a custom fields jobs has failed."

    def handle(self, *args, **kwargs):
        """Run through all objects and ensure they are associated with the correct custom fields."""
        content_types = ContentType.objects.filter(FeatureQuery("custom_fields").get_query())

        for content_type in content_types:
            self.stdout.write(self.style.SUCCESS(f"Processing ContentType {content_type}"))
            model = content_type.model_class()
            custom_fields_for_content_type = content_type.custom_fields.all()
            # 2.0 TODO: #824 use cf.slug rather than cf.name
            custom_field_names_for_content_type = [cf.name for cf in custom_fields_for_content_type]
            with transaction.atomic():
                for obj in model.objects.all():
                    obj_changed = False
                    # Provision CustomFields that are not associated with the object
                    for custom_field in custom_fields_for_content_type:
                        # 2.0 TODO: #824 use custom_field.slug rather than custom_field.name
                        if custom_field.name not in obj._custom_field_data:
                            self.stdout.write(f"Adding missing CustomField {custom_field.name} to {obj}")
                            obj._custom_field_data[custom_field.name] = custom_field.default
                            obj_changed = True
                    # Remove any custom fields that are not associated with the content type
                    for field_name in set(obj._custom_field_data) - set(custom_field_names_for_content_type):
                        self.stdout.write(f"Removing invalid CustomField {field_name} from {obj}")
                        del obj._custom_field_data[field_name]
                        obj_changed = True
                    if obj_changed:
                        try:
                            obj.validated_save()
                        except ValidationError:
                            self.stderr.write(self.style.ERROR(f"Failed saving {obj}"))
