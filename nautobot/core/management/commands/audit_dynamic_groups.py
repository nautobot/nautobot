from django.core.exceptions import ValidationError
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
            try:
                dynamic_group.clean_filter()
            except ValidationError as err:
                self.stderr.write(f'    DynamicGroup "{dynamic_group}" has an invalid filter: {err}')
                is_valid = False
                continue
            dynamic_group_model = dynamic_group.content_type.model_class()
            dynamic_group_model_filter = get_filterset_for_model(dynamic_group_model)
            valid_filterset_fields = dynamic_group_model_filter().filters
            filter_data = dynamic_group.filter
            for filter_field in filter_data.keys():
                if filter_field not in valid_filterset_fields:
                    self.stderr.write(
                        f'    DynamicGroup "{dynamic_group}" has an invalid filter field "{filter_field}"'
                    )
                    is_valid = False
        if is_valid:
            self.stdout.write("\n>>> All DynamicGroup filters are validated successfully!")
        else:
            self.stderr.write(
                "\n>>> Please fix the broken filters stated above according to the documentation available at:\n"
                "https://docs.nautobot.com/projects/core/en/stable/user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1/#ui-graphql-and-rest-api-filter-changes\n"
            )
