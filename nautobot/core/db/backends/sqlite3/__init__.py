"""Nautobot's SQLite database backend.

Extends Django's SQLite backend with the SQL functions, feature flags, and compiler behavior that Nautobot's
PostgreSQL- and MySQL-oriented query code relies on, so that the same models and migrations run unchanged on SQLite.

Select it with `NAUTOBOT_DB_ENGINE=django.db.backends.sqlite3`; Nautobot substitutes this backend automatically.
"""
