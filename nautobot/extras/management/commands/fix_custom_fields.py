from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from nautobot.extras.utils import FeatureQuery


class Command(BaseCommand):
    help = "Adds/Removes any custom fields which should or should not exist on an object. This command should not be run unless a custom fields jobs has failed."

    def add_arguments(self, parser):
        parser.add_argument(
            "args",
            metavar="app_label.ModelName",
            nargs="*",
            help="One or more specific models (each prefixed with its app_label) to fix",
        )

    def _get_content_types(self, names):
        """
        Compile a list of content types to be fixed. If no names are specified, all types with custom fields will be included.
        """
        if not names:
            return ContentType.objects.filter(FeatureQuery("custom_fields").get_query())

        content_types = []

        for name in names:
            try:
                app_label, model_name = name.split(".")
            except ValueError:
                raise CommandError(f"Invalid format: {name}. Models must be specified in the form app_label.ModelName.")
            try:
                content_types.append(ContentType.objects.get(app_label=app_label, model=model_name.lower()).id)
            except ContentType.DoesNotExist:
                raise CommandError(f"Unknown model: {name}")

        return ContentType.objects.filter(pk__in=content_types)

    def handle(self, *args, **kwargs):
        """Run through all objects and ensure they are associated with the correct custom fields."""
        content_types = self._get_content_types(args)

        for content_type in content_types:
            self.stdout.write(self.style.SUCCESS(f"Processing ContentType {content_type}"))
            model = content_type.model_class()
            custom_fields_for_content_type = content_type.custom_fields.all()
            if not custom_fields_for_content_type.exists():
                self.stdout.write(f"No custom fields found for {content_type}")
                continue
            custom_field_keys_for_content_type = [cf.key for cf in custom_fields_for_content_type]
            with transaction.atomic():
                for obj in model.objects.iterator():
                    obj_changed = False
                    # Provision CustomFields that are not associated with the object
                    for custom_field in custom_fields_for_content_type:
                        if custom_field.key not in obj._custom_field_data:
                            self.stdout.write(f"Adding missing CustomField {custom_field.key} to {obj}")
                            obj._custom_field_data[custom_field.key] = custom_field.default
                            obj_changed = True
                    # Remove any custom fields that are not associated with the content type
                    for field_name in set(obj._custom_field_data) - set(custom_field_keys_for_content_type):
                        self.stdout.write(f"Removing invalid CustomField {field_name} from {obj}")
                        del obj._custom_field_data[field_name]
                        obj_changed = True
                    if obj_changed:
                        try:
                            obj.validated_save()
                        except ValidationError:
                            self.stderr.write(self.style.ERROR(f"Failed saving {obj}"))
