from collections import defaultdict
from django.db.models import Q
from django.core.management.base import BaseCommand

from nautobot.extras.models import DynamicGroup


class Command(BaseCommand):
    help = "Validate all groups."

    def add_arguments(self, parser):
        parser.add_argument("--group", type=str)

    def handle(self, *args, **kwargs):
        """Run through all groups and ensure the grouping from both side is consistent."""

        groups_members = defaultdict(list)
        groups = dict()
        content_types = set()

        group_queryset = DynamicGroup.objects.all()
        if kwargs["group"]:
            group_queryset = DynamicGroup.objects.filter(slug=kwargs["group"])

        # Store the PK of all members of each groups in a dict
        for group in group_queryset:
            groups_members[str(group.pk)] = [str(pk) for pk in group.get_queryset().values_list("pk", flat=True)]
            groups[str(group.pk)] = group
            content_types.add(group.content_type)

        # Go over all objects of each Models and check if the groups returned by DynamicGroup.objects.get_for_object matches
        # The previous results
        for content_type in content_types:
            model = content_type.model_class()

            for item in model.objects.all():
                item_pk = str(item.pk)

                groups_1 = []
                for group_id, members in groups_members.items():
                    if item_pk in members:
                        groups_1.append(str(group_id))

                groups_2 = [str(pk) for pk in DynamicGroup.objects.get_for_object(item).values_list("pk", flat=True)]

                wrong_groups = set(groups_2) - set(groups_1)
                missing_groups = set(groups_1) - set(groups_2)

                if wrong_groups or missing_groups:
                    print(f">> {item} - {item.pk}")
                    if wrong_groups:
                        print(f"  In get_for_object but not from Group")
                        for group in wrong_groups:
                            print(f"    {groups[group].slug} ({group})")
                    if missing_groups:
                        print(f"  In Group but not get_for_object")
                        for group in missing_groups:
                            print(f"    {groups[group].slug} ({group})")
