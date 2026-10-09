"""SQL compiler for Nautobot's SQLite backend."""

from django.core.exceptions import EmptyResultSet
from django.db.models.sql import compiler as django_compiler
from django.db.models.sql.compiler import (  # noqa: F401  # re-exported for Django's compiler lookup
    SQLAggregateCompiler,
    SQLDeleteCompiler,
    SQLInsertCompiler,
    SQLUpdateCompiler,
)


class SQLCompiler(django_compiler.SQLCompiler):
    """
    Allow ordered and sliced querysets as members of a compound query (`union()` and friends).

    SQLite does not permit ORDER BY, LIMIT, or parentheses on the members of a compound SELECT, and Django's default
    compiler refuses such queries outright. Each member that needs them is wrapped as `SELECT * FROM (...)` instead,
    which SQLite does accept.
    """

    def _get_combinator_part_sql(self, compiler):
        selected = self.query.selected
        if selected is not None and compiler.query.selected is None:
            compiler.query = compiler.query.clone()
            compiler.query.set_values(selected)
        part_sql, part_args = compiler.as_sql(with_col_aliases=True)
        if compiler.query.combinator or compiler.query.is_sliced or compiler.get_order_by():
            part_sql = f"SELECT * FROM ({part_sql})"  # noqa: S608  # hardcoded-sql-expression; compiler-generated SQL
        return part_sql, part_args

    def get_combinator_sql(self, combinator, all):  # pylint: disable=redefined-builtin  # Django's signature
        # Mirrors django.db.models.sql.compiler.SQLCompiler.get_combinator_sql (Django 5.2) without the
        # feature checks that reject ordered or sliced members, and without wrapping members in parentheses.
        compilers = [
            query.get_compiler(self.using, self.connection, self.elide_empty) for query in self.query.combined_queries
        ]
        parts = []
        empty_compiler = None
        for compiler in compilers:
            try:
                parts.append(self._get_combinator_part_sql(compiler))
            except EmptyResultSet:
                if combinator == "union" or (combinator == "difference" and parts):
                    empty_compiler = compiler
                    continue
                raise
        if not parts:
            raise EmptyResultSet
        elif len(parts) == 1 and combinator == "union" and self.query.is_sliced:
            # A sliced union with a single member would end up with two LIMIT clauses; force a real union.
            empty_compiler.elide_empty = False
            parts.append(self._get_combinator_part_sql(empty_compiler))
        combinator_sql = self.connection.ops.set_operators[combinator]
        if all and combinator == "union":
            combinator_sql += " ALL"
        sql_parts, args_parts = zip(*parts)
        result = [f" {combinator_sql} ".join(sql_parts)]
        params = [param for part in args_parts for param in part]
        return result, params
