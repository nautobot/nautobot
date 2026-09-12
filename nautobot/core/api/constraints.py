"""Translate explicitly supported database conflicts at the API save boundary."""

from dataclasses import dataclass
import re

from django.db import connections, DEFAULT_DB_ALIAS, models
from rest_framework.exceptions import ValidationError


@dataclass(frozen=True)
class UniqueConstraintError:
    """Describe an expected uniqueness conflict, including conflicts in related models.

    ``detail`` uses serializer field names, which need not belong to ``model``.
    For example, a Rack location update can violate a Device uniqueness constraint.
    Only declare conflicts that the caller can resolve by changing the request.
    """

    model: type
    fields: tuple[str, ...]
    detail: dict[str, str]

    def constraint_names(self, connection):
        """Resolve declared model constraints without database introspection."""
        opts = self.model._meta
        names = {
            constraint.name
            for constraint in opts.constraints
            if isinstance(constraint, models.UniqueConstraint)
            and tuple(constraint.fields) == self.fields
            and not constraint.condition
            and not constraint.expressions
        }
        if self.fields in {tuple(fields) for fields in opts.unique_together}:
            # unique_together uses Django's generated index name, rather than a
            # name declared in Meta. Use the same naming algorithm as migrations.
            # Constructing the editor does not open a transaction or execute SQL.
            columns = [opts.get_field(field).column for field in self.fields]
            names.add(connection.schema_editor()._create_index_name(opts.db_table, columns, suffix="_uniq"))
        return names


def get_constraint_error(exception, serializer, using=DEFAULT_DB_ALIAS):
    """Return a DRF validation error for an explicitly mapped database unique violation.

    Call only after the save transaction has rolled back. No queries, locks, or
    savepoints are added. PostgreSQL provides structured diagnostics. MySQL 8
    identifies the table and key in its duplicate-entry message. Require an exact
    match; unknown constraints and unrecognized diagnostics retain their behavior.
    Bulk create uses a ListSerializer, whose child declares the mappings.
    """
    cause = exception.__cause__
    connection = connections[using]
    if connection.vendor == "postgresql":
        diag = getattr(cause, "diag", None)
        if getattr(diag, "sqlstate", None) != "23505":
            return None
        table, constraint = diag.table_name, diag.constraint_name
    elif connection.vendor == "mysql":
        args = getattr(cause, "args", ())
        if len(args) != 2 or args[0] != 1062 or not isinstance(args[1], str):
            return None
        # The duplicate value can contain quotes, newlines, or "for key" text.
        # Match the final table-qualified key, never text inside that value.
        match = re.fullmatch(r"Duplicate entry '.*' for key '([^'.]+)\.([^'.]+)'", args[1], flags=re.DOTALL)
        if match is None:
            return None
        table, constraint = match.groups()
    else:
        return None

    serializer = getattr(serializer, "child", serializer)
    for conflict in getattr(serializer, "database_constraint_errors", ()):
        if table == conflict.model._meta.db_table and constraint in conflict.constraint_names(connection):
            return ValidationError({field: [message] for field, message in conflict.detail.items()}, code="unique")
    return None
