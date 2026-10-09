from django.db.backends.sqlite3.base import Database
from django.db.backends.sqlite3.features import DatabaseFeatures as SQLiteDatabaseFeatures


class DatabaseFeatures(SQLiteDatabaseFeatures):
    # Provided by the JSON_CONTAINS function registered in `functions.py`.
    supports_json_field_contains = True
    # SQLite raised its default variable limit from 999 to 32766 in 3.32.0.
    max_query_params = 32766 if Database.sqlite_version_info >= (3, 32, 0) else 999
