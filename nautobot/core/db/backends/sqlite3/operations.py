from django.db.backends.sqlite3.operations import DatabaseOperations as SQLiteDatabaseOperations


class DatabaseOperations(SQLiteDatabaseOperations):
    compiler_module = "nautobot.core.db.backends.sqlite3.compiler"
