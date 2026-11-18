Changed default Docker Compose development environment to use PostgreSQL 15 as PostgreSQL 14 has reached end of life. Note that Nautobot itself continues to support PostgreSQL 14 for the time being.
Added support for overriding the PostgreSQL version used by `tasks.py`.
Changed CI to run integration tests (only) against PostgreSQL 18.
