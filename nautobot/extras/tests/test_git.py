from unittest import mock

from django.test import TestCase

from nautobot.utilities.git import GitRepo, convert_git_diff_log_to_list


@mock.patch("nautobot.utilities.git.Repo")
class GitRepoTest(TestCase):
    def test_git_repo(self, RepoMock):
        RepoMock.init.return_value = RepoMock
        RepoMock.create_remote.return_value = ""
        RepoMock.git.diff.return_value = "M\tSample"

        url = "http://localhost.git"
        repo = GitRepo("path", url, clone_initially=False)

        RepoMock.clone_from.assert_not_called()
        RepoMock.init.assert_called()
        RepoMock.create_remote.assert_called()
        RepoMock.create_remote.assert_called_with("origin", url=url)

        self.assertEqual(repo.diff_remote("main"), convert_git_diff_log_to_list(RepoMock.git.diff.return_value))
