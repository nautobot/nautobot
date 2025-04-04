from django.db import NotSupportedError
from django.db.models.lookups import Lookup

from nautobot.dcim.utils import object_to_path_node


class PathContains(Lookup):
    lookup_name = "contains"

    def get_prep_lookup(self):
        self.prepare_rhs = False
        self.rhs = object_to_path_node(self.rhs)
        return super().get_prep_lookup()

    def process_rhs(self, compiler, connection):
        rhs, rhs_params = super().process_rhs(compiler, connection)
        rhs = f"{rhs_params[0]}"
        return rhs, []

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params

        vendor = connection.vendor
        # Mapping of vendor => expr
        sql_map = {
            "postgresql": "%s::jsonb ? '%s'",
            "mysql": "JSON_CONTAINS(%s, '\"%s\"','$')",
        }

        if vendor not in sql_map:
            raise NotSupportedError(f"PathContains not supported by database {vendor}")

        sql_expr = sql_map[vendor]
        sql = sql_expr % (lhs, rhs)

        return sql, params
