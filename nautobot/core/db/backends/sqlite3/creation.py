import multiprocessing

from django.db.backends.sqlite3.creation import DatabaseCreation as SQLiteDatabaseCreation


class DatabaseCreation(SQLiteDatabaseCreation):
    def _clone_test_db(self, suffix, verbosity, keepdb=False):
        """Clone the test database for a parallel worker, checkpointing the write-ahead log first.

        Django clones a file-backed SQLite database by copying the main file. In WAL mode, recently committed pages
        may still be in the `-wal` file, so the copy would be incomplete without a checkpoint.
        """
        if not self.is_in_memory_db(self.connection.settings_dict["NAME"]):
            with self.connection.cursor() as cursor:
                cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        super()._clone_test_db(suffix, verbosity, keepdb=keepdb)

    def setup_worker_connection(self, _worker_id):
        """
        Point a parallel test worker at its clone of the test database.

        Django's handling of the "spawn" start method assumes an in-memory test database and
        loads `<alias>_<worker>.sqlite3` from the working directory, which does not exist when the test database is
        a file. `_clone_test_db()` has already copied a file-backed database to the clone's path, so use that.
        """
        if self.is_in_memory_db(self.connection.settings_dict["NAME"]) or multiprocessing.get_start_method() != "spawn":
            super().setup_worker_connection(_worker_id)
            return
        self.connection.settings_dict.update(self.get_test_db_clone_settings(str(_worker_id)))
        self.connection.close()
