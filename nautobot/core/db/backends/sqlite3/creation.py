import multiprocessing

from django.db.backends.sqlite3.creation import DatabaseCreation as SQLiteDatabaseCreation


class DatabaseCreation(SQLiteDatabaseCreation):
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
