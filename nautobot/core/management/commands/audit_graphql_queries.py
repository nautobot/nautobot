from django.core.management.base import BaseCommand

from nautobot.core.graphql import execute_query
from nautobot.users.models import User


class Command(BaseCommand):
    help = "Audit all existing GraphQLQuery instances in the database and output invalid filter data"

    def handle(self, *args, **options):
        from nautobot.extras.models import GraphQLQuery

        self.stdout.write("\n>>> Auditing existing GraphQLQuery data for invalid filters ...\n")

        graph_ql_querys = GraphQLQuery.objects.all().order_by("name")
        user = User.objects.create(username="test_user_1")
        is_valid = True
        for graph_ql_query in graph_ql_querys:
            result = execute_query(graph_ql_query.query, user=user).to_dict()
            if result.get("errors"):
                self.stderr.write(
                    f'    GraphQLQuery {graph_ql_query.name} has an invalid filter: {result.get("errors")}'
                )
                is_valid = False
        if is_valid:
            self.stdout.write("\n>>> All GraphQLQuery filters are validated successfully!")
        else:
            self.stderr.write(
                "\n>>> Please fix the broken filters stated above according to the documentation available at:\n"
                "<nautobot-home>/static/docs/installation/upgrading-from-nautobot-v1.html#ui-graphql-and-rest-api-filter-changes\n"
            )
        User.objects.get(username="test_user_1").delete()
