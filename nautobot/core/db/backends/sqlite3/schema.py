from django.db.backends.sqlite3.schema import DatabaseSchemaEditor as SQLiteDatabaseSchemaEditor


class DatabaseSchemaEditor(SQLiteDatabaseSchemaEditor):
    """
    Preserve composite indexes declared through the retired `index_together` Meta option across table rebuilds.

    Django 5.1 removed `index_together` from model Meta but still accepts historical `AlterIndexTogether`
    migrations. On PostgreSQL and MySQL such an index simply lives on, since those backends alter tables in place.
    SQLite rebuilds the whole table for most alterations, and the rebuilt table only receives the indexes that the
    current model declares, so these historical indexes vanish and a later `RenameIndex(old_fields=...)` cannot find
    them. This editor records the plain composite indexes before a rebuild and recreates any that went missing.
    """

    def _remake_table(self, model, *args, **kwargs):
        table = model._meta.db_table
        indexes_before = self._plain_composite_indexes(table)
        super()._remake_table(model, *args, **kwargs)
        if not indexes_before:
            return
        indexes_after = self._plain_composite_indexes(table)
        with self.connection.cursor() as cursor:
            columns = {column.name for column in self.connection.introspection.get_table_description(cursor, table)}
        for name, index_columns in indexes_before.items():
            if name in indexes_after or not set(index_columns).issubset(columns):
                continue
            quoted_columns = ", ".join(self.quote_name(column) for column in index_columns)
            self.execute(f"CREATE INDEX {self.quote_name(name)} ON {self.quote_name(table)} ({quoted_columns})")

    def _plain_composite_indexes(self, table):
        """Return `{index_name: (column, ...)}` for the non-unique, multi-column indexes on `table`."""
        with self.connection.cursor() as cursor:
            constraints = self.connection.introspection.get_constraints(cursor, table)
        return {
            name: tuple(details["columns"])
            for name, details in constraints.items()
            if details["index"]
            and not details["unique"]
            and not details["primary_key"]
            and details["columns"]
            and len(details["columns"]) > 1
        }
