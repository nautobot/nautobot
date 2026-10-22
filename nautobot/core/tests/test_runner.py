"""Regression tests for filesystem isolation in the test runner (no database required)."""

from contextlib import contextmanager, ExitStack
import os
from pathlib import Path
import shutil
import tempfile
from unittest import mock, TestCase, TestResult, TestSuite

from django.conf import settings
from django.test import override_settings

from nautobot.core.celery import _import_jobs_from_git_repositories
from nautobot.core.tests import runner as test_runner


class GitRootIsolationTest(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(self.directory.cleanup)
        self.development_root = Path(self.directory.name) / "custom development git"
        self.protected_clone = self.make_clone(self.development_root, "production-repository")
        self.marker = self.protected_clone / "DO_NOT_DELETE.txt"
        self.marker_time = self.marker.stat().st_mtime_ns
        self.settings = override_settings(GIT_ROOT=self.development_root)
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        # Exercise the real filesystem scanner with an empty test database's query results.
        query = mock.MagicMock()
        query.exists.return_value = False
        self.queries = mock.patch("nautobot.extras.models.GitRepository.objects.filter", return_value=query)
        self.queries.start()
        self.addCleanup(self.queries.stop)

    @staticmethod
    def make_clone(root, slug):
        clone = Path(root) / slug
        (clone / ".git").mkdir(parents=True)
        (clone / "DO_NOT_DELETE.txt").write_bytes(b"protected repository contents\n")
        return clone

    def assert_development_untouched(self):
        self.assertEqual(settings.GIT_ROOT, self.development_root)
        self.assertTrue((self.protected_clone / ".git").is_dir())
        self.assertEqual(self.marker.read_bytes(), b"protected repository contents\n")
        self.assertEqual(self.marker.stat().st_mtime_ns, self.marker_time)

    def run_tests(self, runner, **callbacks):
        """Drive Django's real run_tests lifecycle without creating a database or nesting its environment."""
        defaults = {
            "setup_test_environment": None,
            "build_suite": TestSuite(),
            "get_databases": {},
            "setup_databases": [],
            "run_checks": None,
            "run_suite": TestResult(),
            "teardown_databases": None,
            "teardown_test_environment": None,
        }
        with ExitStack() as stack:
            for name, value in defaults.items():
                replacement = stack.enter_context(mock.patch.object(runner, name, return_value=value))
                if name in callbacks:
                    replacement.side_effect = callbacks[name]
            return runner.run_tests([])

    def test_isolation_precedes_database_creation_and_survives_repeated_keepdb_runs(self):
        roots = []

        def create_database(**kwargs):
            root = Path(settings.GIT_ROOT)
            self.assertNotEqual(root, self.development_root)
            self.assertTrue(root.is_dir())
            roots.append(root)
            # A migration-time scan must only remove unmanaged clones from this run.
            clone = self.make_clone(root, "unmanaged-test-repository")
            _import_jobs_from_git_repositories()
            self.assertFalse(clone.exists())
            self.assertTrue(self.marker.is_file())
            self.make_clone(root, "test-repository")

        for keepdb in (False, True, True):
            with self.subTest(keepdb=keepdb):
                runner = test_runner.NautobotTestRunner(verbosity=0, keepdb=keepdb)
                self.assertEqual(self.run_tests(runner, setup_databases=create_database), 0)
                self.assertFalse(roots[-1].parent.exists())
                self.assert_development_untouched()
        self.assertEqual(len(set(roots)), 3)

    def test_actual_database_setup_is_isolated(self):
        runner = test_runner.NautobotTestRunner(verbosity=0)
        connection = mock.MagicMock()

        def create_test_db(**kwargs):
            self.assertNotEqual(Path(settings.GIT_ROOT), self.development_root)
            _import_jobs_from_git_repositories()
            self.assertTrue(self.marker.exists())

        connection.creation.create_test_db.side_effect = create_test_db
        with (
            override_settings(TEST_USE_FACTORIES=False),
            mock.patch.object(test_runner, "has_coverage", False),
            mock.patch.object(test_runner, "connections", {"default": connection}),
            mock.patch.object(
                test_runner, "get_unique_databases_and_mirrors", return_value=({"db": ("db", ["default"])}, {})
            ),
        ):
            self.run_tests(runner, setup_databases=lambda **kwargs: type(runner).setup_databases(runner, **kwargs))
        connection.creation.create_test_db.assert_called_once()
        self.assert_development_untouched()

    def test_original_root_need_not_exist(self):
        missing = Path(self.directory.name) / "missing"
        with override_settings(GIT_ROOT=missing):
            self.run_tests(test_runner.NautobotTestRunner(verbosity=0))
            self.assertEqual(settings.GIT_ROOT, missing)
            self.assertFalse(missing.exists())
        self.assert_development_untouched()

    def test_cleanup_on_lifecycle_exceptions(self):
        roots = []
        for phase in (
            "setup_test_environment",
            "build_suite",
            "setup_databases",
            "run_checks",
            "run_suite",
            "teardown_databases",
            "teardown_test_environment",
        ):
            roots.clear()

            def fail(*args, **kwargs):
                roots.append(Path(settings.GIT_ROOT))
                self.assertNotEqual(roots[-1], self.development_root)
                raise RuntimeError("deliberate lifecycle failure")

            with self.subTest(phase=phase), self.assertRaisesRegex(RuntimeError, "deliberate lifecycle failure"):
                self.run_tests(test_runner.NautobotTestRunner(verbosity=0), **{phase: fail})
            self.assertFalse(roots[0].parent.exists())
            self.assert_development_untouched()

    def test_cleanup_on_failed_test(self):
        roots = []

        def fail_test(suite):
            roots.append(Path(settings.GIT_ROOT))
            result = TestResult()
            result.failures.append((None, "deliberate assertion failure"))
            return result

        self.assertEqual(self.run_tests(test_runner.NautobotTestRunner(verbosity=0), run_suite=fail_test), 1)
        self.assertFalse(roots[0].parent.exists())
        self.assert_development_untouched()

    def test_cleanup_error_restores_settings(self):
        unlink = os.unlink
        roots = []

        def create_locked_file(suite):
            root = Path(settings.GIT_ROOT)
            roots.append(root.parent)
            (root / "locked-file").touch()
            return TestResult()

        def inaccessible(path, *args, **kwargs):
            if Path(path).name == "locked-file":
                raise PermissionError("simulated open file on Windows")
            return unlink(path, *args, **kwargs)

        with mock.patch("os.unlink", side_effect=inaccessible):
            self.run_tests(test_runner.NautobotTestRunner(verbosity=0), run_suite=create_locked_file)
        self.assert_development_untouched()
        self.assertTrue((roots[0] / "parent" / "locked-file").exists())
        shutil.rmtree(roots[0])

    @contextmanager
    def worker_process_settings(self):
        """Undo process-lifetime overrides when simulating a worker inside this test process."""
        with ExitStack() as stack:

            def worker_override(**kwargs):
                context = override_settings(**kwargs)
                stack.callback(context.disable)
                return context

            with mock.patch.object(test_runner, "override_settings", side_effect=worker_override):
                yield

    def test_parallel_workers_and_parent_cannot_scan_each_others_clones(self):
        roots = []
        original_caches = settings.CACHES

        def run_workers(suite):
            parent_root = Path(settings.GIT_ROOT)
            parent_clone = self.make_clone(parent_root, "parent-repository")
            for worker_id in (1, 2):
                # Scope process-local overrides to simulate independent forked processes in this unit test.
                with self.worker_process_settings():
                    with (
                        mock.patch.object(test_runner, "_init_worker"),
                        mock.patch("django.test.runner._worker_id", worker_id),
                    ):
                        test_runner.init_worker_with_unique_cache(
                            None,
                            process_setup=test_runner._setup_worker_git_root,
                            process_setup_args=(parent_root.parent,),
                        )
                    roots.append(Path(settings.GIT_ROOT))
                    self.assertNotEqual(roots[-1], parent_root)
                    self.assertEqual(roots[-1].parent, parent_root.parent)
                    self.assertEqual(
                        settings.CACHES["default"]["LOCATION"],
                        test_runner.parse_redis_connection(redis_database=worker_id + 1),
                    )
                    _import_jobs_from_git_repositories()
                    self.assertTrue(parent_clone.exists())
                    if worker_id == 2:
                        self.assertTrue((roots[0] / "worker-repository").exists())
                    self.make_clone(roots[-1], "worker-repository")
            _import_jobs_from_git_repositories()
            self.assertFalse(parent_clone.exists())
            for root in roots:
                self.assertTrue((root / "worker-repository").exists())
            return TestResult()

        self.run_tests(test_runner.NautobotTestRunner(verbosity=0, parallel=2), run_suite=run_workers)
        self.assertEqual(len(set(roots)), 2)
        self.assertTrue(all(not root.exists() for root in roots))
        self.assertIs(settings.CACHES, original_caches)
        self.assert_development_untouched()

    def test_spawn_worker_is_isolated_before_django_setup(self):
        roots = []

        def run_worker(suite):
            parent_root = Path(settings.GIT_ROOT)
            parallel_suite = test_runner.NautobotParallelTestSuite([], 2)
            with mock.patch.object(test_runner.ParallelTestSuite, "run"):
                parallel_suite.run(TestResult())
            self.assertEqual(parallel_suite.process_setup_args, (str(parent_root.parent),))

            def django_setup():
                roots.append(Path(settings.GIT_ROOT))
                self.assertNotEqual(roots[-1], parent_root)
                self.assertEqual(roots[-1].parent, parent_root.parent)
                _import_jobs_from_git_repositories()
                self.assertTrue(self.marker.exists())

            counter = mock.MagicMock(value=0)
            with (
                self.worker_process_settings(),
                mock.patch("django.test.runner.multiprocessing.get_start_method", return_value="spawn"),
                mock.patch("django.test.runner.django.setup", side_effect=django_setup) as setup,
                mock.patch("django.test.runner.setup_test_environment"),
                mock.patch("django.test.runner._worker_id", 0),
            ):
                test_runner.init_worker_with_unique_cache(
                    counter,
                    process_setup=parallel_suite.process_setup.__func__,
                    process_setup_args=parallel_suite.process_setup_args,
                    used_aliases=[],
                )
                setup.assert_called_once()
                self.assertEqual(list(parent_root.parent.glob("worker-*")), [roots[-1]])
            return TestResult()

        self.run_tests(test_runner.NautobotTestRunner(verbosity=0, parallel=2), run_suite=run_worker)
        self.assertFalse(roots[0].parent.exists())
        self.assert_development_untouched()

    def test_worker_initialization_failure_is_cleaned_up_by_parent(self):
        roots = []

        def fail_initialization(*args, **kwargs):
            roots.append(Path(settings.GIT_ROOT))
            self.assertNotEqual(roots[-1], self.development_root)
            raise RuntimeError("worker initialization failed")

        def run_worker(suite):
            owner = Path(settings.GIT_ROOT).parent
            with (
                self.worker_process_settings(),
                mock.patch.object(test_runner, "_init_worker", side_effect=fail_initialization),
            ):
                test_runner.init_worker_with_unique_cache(
                    None, process_setup=test_runner._setup_worker_git_root, process_setup_args=(owner,)
                )

        with self.assertRaisesRegex(RuntimeError, "worker initialization failed"):
            self.run_tests(test_runner.NautobotTestRunner(verbosity=0, parallel=2), run_suite=run_worker)
        self.assertFalse(roots[0].parent.exists())
        self.assert_development_untouched()

    def test_worker_does_not_need_to_inherit_parent_settings(self):
        roots = []

        def run_worker(suite):
            owner = Path(settings.GIT_ROOT).parent
            # A fresh interpreter initially sees the configured development GIT_ROOT.
            with override_settings(GIT_ROOT=self.development_root), self.worker_process_settings():
                with mock.patch.object(test_runner, "_init_worker"), mock.patch("django.test.runner._worker_id", 1):
                    test_runner.init_worker_with_unique_cache(
                        None, process_setup=test_runner._setup_worker_git_root, process_setup_args=(owner,)
                    )
                roots.append(Path(settings.GIT_ROOT))
                self.assertEqual(roots[-1].parent, owner)
                self.assertNotEqual(roots[-1], self.development_root)
                _import_jobs_from_git_repositories()
            return TestResult()

        self.run_tests(test_runner.NautobotTestRunner(verbosity=0, parallel=2), run_suite=run_worker)
        self.assertFalse(roots[0].parent.exists())
        self.assert_development_untouched()

    def test_production_cleanup_and_job_refresh_remain_enabled(self):
        git_root = Path(self.directory.name) / "scanner-regression"
        clone = self.make_clone(git_root, "unmanaged-repository")
        repository = mock.Mock(pk="repository-pk", current_head="head")
        query = mock.MagicMock()
        query.exists.return_value = False
        query.__iter__.return_value = iter([repository])
        with (
            override_settings(GIT_ROOT=git_root),
            mock.patch("nautobot.extras.models.GitRepository.objects.filter", return_value=query),
            mock.patch("nautobot.core.celery.refresh_git_repository") as refresh,
        ):
            _import_jobs_from_git_repositories()
        self.assertFalse(clone.exists())
        refresh.assert_called_once_with(state=None, repository_pk="repository-pk", head="head")
        self.assert_development_untouched()
