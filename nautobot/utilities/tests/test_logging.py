from nautobot.utilities.logging import sanitize
from nautobot.utilities.testing import TestCase


class LoggingUtilitiesTest(TestCase):

    DIRTY_CLEAN = (
        # should match first default pattern
        ("http://user:password@localhost", "http://(redacted)@localhost"),
        ("HTTPS://:password@EXAMPLE.COM", "HTTPS://(redacted)@EXAMPLE.COM"),
        # should match second default pattern
        ("username myusername, password mypassword", "username (redacted) password (redacted)"),
        ("Username: me Password: you", "Username: (redacted) Password: (redacted)"),
        ("My username is someuser", "My username is (redacted)"),
        ("My password is: supersecret!123", "My password is: (redacted)"),
        # both patterns need to be applied together
        (
            "I use username FOO and password BAR to log in as https://FOO:BAR@example.com",
            "I use username (redacted) and password (redacted) to log in as https://(redacted)@example.com",
        ),
    )

    def test_sanitize_default_coverage(self):
        """Test that the default sanitizer patterns cover a variety of cases."""
        for dirty, clean in self.DIRTY_CLEAN:
            self.assertEqual(sanitize(dirty), clean)

    def test_sanitize_idempotent(self):
        """Test that sanitizing the same string repeatedly doesn't cascade oddly."""
        for dirty, clean in self.DIRTY_CLEAN:
            self.assertEqual(sanitize(sanitize(dirty)), clean)
