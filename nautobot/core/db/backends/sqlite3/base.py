from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import DEFAULT_DB_ALIAS
from django.db.backends.sqlite3 import base as django_sqlite3

from nautobot.core.db.backends.sqlite3.creation import DatabaseCreation
from nautobot.core.db.backends.sqlite3.features import DatabaseFeatures
from nautobot.core.db.backends.sqlite3.functions import register_functions
from nautobot.core.db.backends.sqlite3.lookups import register_lookups
from nautobot.core.db.backends.sqlite3.operations import DatabaseOperations
from nautobot.core.db.backends.sqlite3.schema import DatabaseSchemaEditor

if getattr(settings, "METRICS_ENABLED", False):
    from django_prometheus.db.backends.sqlite3.base import DatabaseWrapper as _BaseDatabaseWrapper
else:
    _BaseDatabaseWrapper = django_sqlite3.DatabaseWrapper

# The JSON "->" operator used by the lookups in `lookups.py` arrived in SQLite 3.38.0.
MINIMUM_SQLITE_VERSION = (3, 38, 0)

if django_sqlite3.Database.sqlite_version_info < MINIMUM_SQLITE_VERSION:
    raise ImproperlyConfigured(
        f"Nautobot requires SQLite {'.'.join(str(part) for part in MINIMUM_SQLITE_VERSION)} or later "
        f"(found {django_sqlite3.Database.sqlite_version})."
    )

register_lookups()


# Connection defaults suited to several processes (web workers, Celery worker, beat) sharing one database file.
# Each can be overridden through DATABASES["default"]["OPTIONS"].
DEFAULT_OPTIONS = {
    # Seconds to wait for a lock held by another connection before failing. Django's default is 5.
    "timeout": 15,
    # Write-ahead logging lets readers proceed while a writer is active; NORMAL sync is the usual pairing with WAL.
    "init_command": "PRAGMA journal_mode = WAL; PRAGMA synchronous = NORMAL",
}
# Take the write lock when a transaction begins rather than at its first write, so that concurrent writers queue
# instead of one of them failing partway through. Not applied to a `TEST` mirror of another alias, where it would
# contend with that alias for the same lock in the same thread (the test runner wraps both in transactions).
DEFAULT_TRANSACTION_MODE = "IMMEDIATE"


class DatabaseWrapper(_BaseDatabaseWrapper):
    display_name = "SQLite (Nautobot)"
    creation_class = DatabaseCreation
    features_class = DatabaseFeatures
    ops_class = DatabaseOperations
    SchemaEditorClass = DatabaseSchemaEditor

    def __init__(self, settings_dict, alias=DEFAULT_DB_ALIAS):
        options = settings_dict.setdefault("OPTIONS", {})
        for key, value in DEFAULT_OPTIONS.items():
            options.setdefault(key, value)
        if not settings_dict.get("TEST", {}).get("MIRROR"):
            options.setdefault("transaction_mode", DEFAULT_TRANSACTION_MODE)
        super().__init__(settings_dict, alias)

    def get_new_connection(self, conn_params):
        conn = super().get_new_connection(conn_params)
        register_functions(conn)
        return conn
