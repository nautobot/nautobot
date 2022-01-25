from nautobot.utilities.testing.integration import SplinterTestCase


class JobTestCase(SplinterTestCase):
    """
    Integration tests to test a job's soft_time_limit
    """

    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()
        self.login(self.user.username, self.password)

    def tearDown(self):
        self.logout()
        super().tearDown()

    def test_soft_time_limit_immediate_run(self):
        self.browser.visit(self.live_server_url)
        self.assertTrue(self.browser.is_text_present("Organization"))
