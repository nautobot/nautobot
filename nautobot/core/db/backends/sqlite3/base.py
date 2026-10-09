from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
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


class DatabaseWrapper(_BaseDatabaseWrapper):
    display_name = "SQLite (Nautobot)"
    creation_class = DatabaseCreation
    features_class = DatabaseFeatures
    ops_class = DatabaseOperations
    SchemaEditorClass = DatabaseSchemaEditor

    def get_new_connection(self, conn_params):
        conn = super().get_new_connection(conn_params)
        register_functions(conn)
        return conn
