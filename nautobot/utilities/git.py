"""General-purpose Git utilities."""

from collections import namedtuple
import logging
import os

from git import Repo


logger = logging.getLogger("nautobot.utilities.git")

# namedtuple takes a git log diff status and its accompanying text.
GitDiffLog = namedtuple("GitDiffLog", ["status", "text"])

# 'A' and 'D' status are swapped because of the way the repo.git.diff was implemented
# e.g. 'A' actually stands for Addition but in this case is Deletion
GIT_STATUS_MAP = {
    "A": "Deletion",
    "M": "Modification",
    "C": "Copy",
    "D": "Addition",
    "R": "Renaming",
    "T": "File Type Changed",
    "U": "File Unmerged",
    "X": "Unknown",
}


def swap_status_initials(data):
    """Swap Git status initials with its equivalent."""
    initial, text = data.split("\t")
    return GitDiffLog(status=GIT_STATUS_MAP.get(initial), text=text)


def convert_git_diff_log_to_list(logs):
    """
    Convert Git diff log into a list splitted by \\n

    Example:
        >>> git_log = "M\tindex.html\nR\tsample.txt"
        >>> print(convert_git_diff_log_to_list(git_log))
        ["Modification - index.html", "Renaming - sample.txt"]
    """
    logs = logs.split("\n")
    return [swap_status_initials(line) for line in logs]


class BranchDoesNotExist(Exception):
    pass


class GitRepo:
    def __init__(self, path, url, clone_initially=True):
        """
        Ensure that we have a clone of the given remote Git repository URL at the given local directory path.

        Args:
            path (str): path to git repo
            url (str): git repo url
            clone_initially (bool): True if the repo needs to be cloned
        """
        if os.path.isdir(path):
            self.repo = Repo(path=path)
        elif clone_initially:
            self.repo = Repo.clone_from(url, to_path=path)
        else:
            self.repo = Repo.init(path)
            self.repo.create_remote("origin", url=url)

        if url not in self.repo.remotes.origin.urls:
            self.repo.remotes.origin.set_url(url)

    def fetch(self):
        self.repo.remotes.origin.fetch()

    def checkout(self, branch, commit_hexsha=None):
        """
        Check out the given branch, and optionally the specified commit within that branch.
        """
        # Short-circuit logic - do we already have this commit checked out?
        if commit_hexsha and commit_hexsha == self.repo.head.commit.hexsha:
            logger.debug(f"Commit {commit_hexsha} is already checked out.")
            return commit_hexsha

        self.fetch()
        if commit_hexsha:
            # Sanity check - GitPython doesn't provide a handy API for this so we just call a raw Git command:
            # $ git branch origin/<branch> --remotes --contains <commit>
            # prints the branch name if it DOES contain the commit, and nothing if it DOES NOT contain the commit.
            # Since we did a `fetch` and not a `pull` above, we need to check for the commit in the remote origin
            # branch, not the local (not-yet-updated) branch.
            if branch not in self.repo.git.branch(f"origin/{branch}", "--remotes", "--contains", commit_hexsha):
                raise RuntimeError(f"Requested to check out commit `{commit_hexsha}`, but it's not in branch {branch}!")
            logger.info(f"Checking out commit `{commit_hexsha}` on branch `{branch}`...")
            self.repo.git.checkout(commit_hexsha)
            return commit_hexsha

        if branch in self.repo.heads:
            branch_head = self.repo.heads[branch]
        else:
            try:
                branch_head = self.repo.create_head(branch, self.repo.remotes.origin.refs[branch])
                branch_head.set_tracking_branch(self.repo.remotes.origin.refs[branch])
            except IndexError as git_error:
                logger.error(
                    "Branch %s does not exist at %s. %s", branch, list(self.repo.remotes.origin.urls)[0], git_error
                )
                raise BranchDoesNotExist(
                    f"Please create branch '{branch}' in upstream and try again."
                    f" If this is a new repo, please add a commit before syncing. {git_error}"
                )

        logger.info(f"Checking out latest commit on branch `{branch}`...")
        branch_head.checkout()
        # No specific commit hash was given, so make sure we get the latest from origin
        # We would use repo.remotes.origin.pull() here, but that will fail in the case where someone has
        # force-pushed to the upstream repo since the last time we did a pull. To be safe, we reset instead.
        self.repo.head.reset(f"origin/{branch}", index=True, working_tree=True)
        commit_hexsha = self.repo.head.reference.commit.hexsha
        logger.info(f"Latest commit on branch `{branch}` is `{commit_hexsha}`")
        return commit_hexsha

    def diff_remote(self, branch):
        logger.debug("Fetching from remote.")
        self.fetch()

        try:
            self.repo.remotes.origin.refs[branch]
        except IndexError as git_error:
            logger.error(
                "Branch %s does not exist at %s. %s", branch, list(self.repo.remotes.origin.urls)[0], git_error
            )
            raise BranchDoesNotExist(
                f"Please create branch '{branch}' in upstream and try again."
                f" If this is a new repo, please add a commit before syncing. {git_error}"
            )

        logger.debug("Getting diff between local branch and remote branch")
        diff = self.repo.git.diff("--name-status", f"origin/{branch}")
        if diff:  # if diff is not empty
            return convert_git_diff_log_to_list(diff)
        logger.debug("No Difference")
        return []
