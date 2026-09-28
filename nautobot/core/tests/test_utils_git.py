"""Tests for `nautobot.core.utils.git`."""

import tempfile

from nautobot.core.testing import TestCase
from nautobot.core.utils.git import BranchDoesNotExist, GitRepo
from nautobot.extras.tests.git_helper import create_and_populate_git_repository


class GitRepoTestCase(TestCase):
    """Tests verifying logic in the `GitRepo` helper class."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._remote_dir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        create_and_populate_git_repository(cls._remote_dir.name)
        cls.remote_url = "file://" + cls._remote_dir.name

    @classmethod
    def tearDownClass(cls):
        cls._remote_dir.cleanup()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self._local_dir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(self._local_dir.cleanup)
        self.repo = GitRepo(self._local_dir.name, self.remote_url, branch="main")

    def test_init_rejects_invalid_branch(self):
        """`GitRepo(branch=...)` rejects whitespace / dash-prefixed values before invoking git clone."""
        cases = [
            ("", "branch must be a non-empty string"),
            (" main", "must not contain whitespace"),
            ("main\n", "must not contain whitespace"),
            ("--upload-pack=evil", r"must not start with '-'"),
        ]
        for value, message_regex in cases:
            with self.subTest(branch=value):
                with tempfile.TemporaryDirectory() as fresh_dir:
                    with self.assertRaisesRegex(ValueError, message_regex):
                        GitRepo(fresh_dir, self.remote_url, branch=value)

    def test_init_accepts_none_branch(self):
        """`branch=None` (the default) means "clone the remote's default branch" and must remain accepted."""
        with tempfile.TemporaryDirectory() as fresh_dir:
            repo = GitRepo(fresh_dir, self.remote_url, branch=None)
            self.assertEqual(repo.head, self.repo.head)

    def test_checkout_rejects_invalid_branch(self):
        """`branch` must be a non-empty string with no whitespace and no leading dash."""
        cases = [
            ("", "branch must be a non-empty string"),
            (None, "branch must be a non-empty string"),
            (" main", "must not contain whitespace"),
            ("main\n", "must not contain whitespace"),
            ("ma in", "must not contain whitespace"),
            ("\tmain", "must not contain whitespace"),
            ("--orphan", r"must not start with '-'"),
            ("-h", r"must not start with '-'"),
        ]
        for value, message_regex in cases:
            with self.subTest(branch=value):
                with self.assertRaisesRegex(ValueError, message_regex):
                    self.repo.checkout(value)

    def test_checkout_rejects_invalid_commit_hexsha(self):
        """Non-empty `commit_hexsha` must not contain whitespace or start with a dash.

        We only enforce the CLI-injection-shape rules here; strict hex validation lives on
        `GitRepository.current_head` where the value is genuinely a commit hash.
        """
        cases = [
            ("--detach", r"must not start with '-'"),
            ("-f", r"must not start with '-'"),
            ("abc def", "must not contain whitespace"),
            ("abc\n", "must not contain whitespace"),
        ]
        for value, message_regex in cases:
            with self.subTest(commit_hexsha=value):
                with self.assertRaisesRegex(ValueError, message_regex):
                    self.repo.checkout("main", commit_hexsha=value)

    def test_checkout_accepts_empty_commit_hexsha_as_unspecified(self):
        """Empty `commit_hexsha` is treated as "not provided" — callers pass `repo.current_head`,
        which is "" for repos that have never been synced. Must remain accepted for backwards compat.
        """
        head, changed = self.repo.checkout("main", commit_hexsha="")
        self.assertTrue(changed)
        self.assertEqual(head, self.repo.head)

    def test_checkout_short_hex_branch_not_treated_as_commit(self):
        """A 1-3 char hex-only `branch` like "abc" should not be misinterpreted as a commit hash.

        Previously the `set(branch).issubset(string.hexdigits)` heuristic admitted any hex-only
        string and handed it to `git checkout`, producing a cryptic GitCommandError. After
        hardening, such a value (when it isn't a real branch/tag) surfaces as `BranchDoesNotExist`.
        """
        for value in ("a", "ab", "abc"):
            with self.subTest(branch=value):
                with self.assertRaises(BranchDoesNotExist):
                    self.repo.checkout(value)

    def test_checkout_accepts_valid_refs(self):
        """Sanity check: real branch and tag names still check out successfully after validation."""
        for value in ("main", "valid-files"):
            with self.subTest(ref=value):
                head, _ = self.repo.checkout(value)
                self.assertEqual(head, self.repo.head)

    def test_diff_remote_rejects_invalid_branch(self):
        """`diff_remote()` validates `branch` the same way `checkout()` does."""
        cases = [
            ("", "branch must be a non-empty string"),
            (None, "branch must be a non-empty string"),
            (" main", "must not contain whitespace"),
            ("--orphan", r"must not start with '-'"),
        ]
        for value, message_regex in cases:
            with self.subTest(branch=value):
                with self.assertRaisesRegex(ValueError, message_regex):
                    self.repo.diff_remote(value)
