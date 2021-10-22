from nautobot.utilities.testing.tables import TableTestCase

import nautobot.extras.tables as MUT


class TableValidationTest(TableTestCase):
    def test_tables_properly_defined(self):
        tables = self.get_tables_from_module(MUT)
        for t in tables:
            self.assertTableFieldsExist(t)
