from django.db import NotSupportedError
from django.db.models.lookups import Lookup, Contains

from nautobot.dcim.utils import object_to_path_node


class PathContains(Lookup):
    lookup_name = "contains"

    def get_prep_lookup(self):
        self.prepare_rhs = False
        self.rhs = object_to_path_node(self.rhs)
        return super().get_prep_lookup()

    def process_rhs(self, compiler, connection):
        rhs, rhs_params = super().process_rhs(compiler, connection)
        rhs = "%s" % rhs_params[0]
        return rhs, []

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params

        engine = connection.settings_dict["ENGINE"]
        if "postgres" in engine:
            sql = "%s::jsonb ? '%s'" % (lhs, rhs)
        elif "mysql" in engine:
            sql = "JSON_CONTAINS(%s, '\"%s\"','$')" % (lhs, rhs)
        else:
            raise NotSupportedError("PathContains only supports PostgreSQL and MySQL")

        return sql, params
