from django.core.management.base import BaseCommand

from nautobot.core.utils.lookup import get_filterset_for_model


class Command(BaseCommand):
    help = "Audit all existing DynamicGroup instances in the database and output invalid filter data"

    def handle(self, *args, **options):
        from nautobot.extras.models import DynamicGroup

        self.stdout.write("\n>>> Auditing existing DynamicGroup data for invalid filters ...\n")

        dynamic_groups = DynamicGroup.objects.all().order_by("name")
        is_valid = True
        for dynamic_group in dynamic_groups:
            dynamic_group_model = dynamic_group.content_type.model_class()
            dynamic_group_model_filter = get_filterset_for_model(dynamic_group_model)
            valid_filterset_fields = dynamic_group_model_filter().filters
            filter_data = dynamic_group.filter
            for filter_field in filter_data.keys():
                if filter_field not in valid_filterset_fields:
                    self.stdout.write(
                        f"    DynamicGroup instance with name `{dynamic_group.name}` and content type `{dynamic_group.content_type}` has an invalid filter `{filter_field}`"
                    )
                    is_valid = False
        if is_valid:
            self.stdout.write("\n>>> All DynamicGroup filters are validated successfully!")
        else:
            self.stdout.write(
                "\n>>> Please fix the broken filters stated above according to the documentation available at:\n"
                "<nautobot-home>/static/docs/installation/upgrading-from-nautobot-v1.html#ui-graphql-and-rest-api-filter-changes\n"
            )
