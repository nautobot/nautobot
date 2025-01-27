"""General-purpose Git utilities."""

from collections import namedtuple
import logging
import os
import string

from git import Repo

from nautobot.core.utils.logging import sanitize

logger = logging.getLogger(__name__)

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

# Environment variables to set on appropriate `git` CLI calls
GIT_ENVIRONMENT = {
    "GIT_TERMINAL_PROMPT": "0",  # never prompt for user input such as credentials - important to avoid hangs!
}


def swap_status_initials(data):
    """Swap Git status initials with its equivalent."""
    initial, text = data.split("\t", 1)
    return GitDiffLog(status=GIT_STATUS_MAP.get(initial[0]), text=text)


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
    def __init__(self, path, url, clone_initially=True, branch=None, depth=0):
        """
        Ensure that we have a clone of the given remote Git repository URL at the given local directory path.

        Args:
            path (str): path to git repo
            url (str): git repo url
            clone_initially (bool): True if the repo needs to be cloned
            branch (str): branch to checkout
            depth (int): depth of the clone
        """
        self.url = url
        self.sanitized_url = sanitize(url)
        if os.path.isdir(path) and os.path.isdir(os.path.join(path, ".git")):
            self.repo = Repo(path=path)
        elif clone_initially:
            # Don't log `url` as it may include authentication details.
            logger.debug("Cloning git repository to %s...", path)
            if not depth:
                self.repo = Repo.clone_from(url, to_path=path, env=GIT_ENVIRONMENT, branch=branch)
            else:
                self.repo = Repo.clone_from(url, to_path=path, env=GIT_ENVIRONMENT, branch=branch, depth=depth)
        else:
            self.repo = Repo.init(path)
            self.repo.create_remote("origin", url=url)

        if url not in self.repo.remotes.origin.urls:
            self.repo.remotes.origin.set_url(url)

    @property
    def head(self):
        """Current checked out repository head commit."""
        return self.repo.head.commit.hexsha

    def fetch(self):
        with self.repo.git.custom_environment(**GIT_ENVIRONMENT):
            self.repo.remotes.origin.fetch()

    def checkout(self, branch, commit_hexsha=None):
        """
        Check out the given branch, and optionally the specified commit within that branch.

        Args:
            branch (str): A branch name, a tag name, or a (possibly abbreviated) commit identifier.
            commit_hexsha (str): A specific (possibly abbreviated) commit identifier.

        If `commit_hexsha` is specified and `branch` is either a tag or a commit identifier, they must match.
        If `commit_hexsha` is specified and `branch` is a branch name, it must contain the specified commit.

        Returns:
            (str, bool): commit_hexsha the repo contains now, and whether any change occurred
        """
        # Short-circuit logic - do we already have this commit checked out?
        if commit_hexsha and self.head.startswith(commit_hexsha):
            logger.debug(f"Commit {commit_hexsha} is already checked out.")
            return (self.head, False)
        # User might specify the commit as a "branch" name...
        if not commit_hexsha and set(branch).issubset(string.hexdigits) and self.head.startswith(branch):
            logger.debug("Commit %s is already checked out.", branch)
            return (self.head, False)

        self.fetch()
        # Is `branch` actually a branch, a tag, or a commit? Heuristics:
        is_branch = branch in self.repo.remotes.origin.refs
        is_tag = branch in self.repo.tags
        maybe_commit = set(branch).issubset(string.hexdigits)
        logger.debug(
            "Branch %s --> is_branch: %s, is_tag: %s, maybe_commit: %s",
            branch,
            is_branch,
            is_tag,
            maybe_commit,
        )

        if is_branch:
            if commit_hexsha:
                # Sanity check - GitPython doesn't provide a handy API for this so we just call a raw Git command:
                # $ git branch origin/<branch> --remotes --contains <commit>
                # prints the branch name if it DOES contain the commit, and nothing if it DOES NOT contain the commit.
                # Since we did a `fetch` and not a `pull` above, we need to check for the commit in the remote origin
                # branch, not the local (not-yet-updated) branch.
                if branch not in self.repo.git.branch(f"origin/{branch}", "--remotes", "--contains", commit_hexsha):
                    raise RuntimeError(
                        f"Requested to check out commit {commit_hexsha}, but it's not part of branch {branch}!"
                    )
                logger.info("Checking out commit %s on branch %s...", commit_hexsha, branch)
                self.repo.git.checkout(commit_hexsha)
                return (self.head, True)

            if branch in self.repo.heads:
                branch_head = self.repo.heads[branch]
            else:
                try:
                    branch_head = self.repo.create_head(branch, self.repo.remotes.origin.refs[branch])
                    branch_head.set_tracking_branch(self.repo.remotes.origin.refs[branch])
                except IndexError as git_error:
                    logger.error(
                        "Branch %s does not exist at %s. %s",
                        branch,
                        next(iter(self.repo.remotes.origin.urls)),
                        git_error,
                    )
                    raise BranchDoesNotExist(
                        f"Please create branch '{branch}' in upstream and try again."
                        f" If this is a new repo, please add a commit before syncing. {git_error}"
                    )

            logger.info("Checking out latest commit on branch %s...", branch)
            branch_head.checkout()
            # No specific commit hash was given, so make sure we get the latest from origin
            # We would use repo.remotes.origin.pull() here, but that will fail in the case where someone has
            # force-pushed to the upstream repo since the last time we did a pull. To be safe, we reset instead.
            self.repo.head.reset(f"origin/{branch}", index=True, working_tree=True)
            logger.info("Latest commit on branch `%s` is `%s`", branch, self.head)
            return (self.head, True)

        if is_tag:
            tag = self.repo.tags[branch]
            if commit_hexsha:
                # Sanity check
                if not tag.commit.hexsha.startswith(commit_hexsha):
                    raise RuntimeError(
                        f"Requested to check out tag {branch} and commit {commit_hexsha} together, "
                        f"but tag {branch} is actually commit {tag.commit.hexsha}!"
                    )
            logger.info("Checking out tag %s...", branch)
            self.repo.git.checkout(branch)
            return (self.head, True)

        if maybe_commit:
            # Sanity check
            if commit_hexsha and not (commit_hexsha.startswith(branch) or branch.startswith(commit_hexsha)):
                raise RuntimeError(
                    f"Requested to check out both {branch} and {commit_hexsha} together, "
                    f"but {branch} is neither a branch, a tag, nor the same commit hash!"
                )

            logger.info("Checking out commit %s...", branch)
            self.repo.git.checkout(branch)
            return (self.head, True)

        # Fallthru
        raise BranchDoesNotExist(
            f"{branch} does not appear to be an existing branch, tag, or possible commit hash. "
            "Please check your upstream repository and the data you are using."
        )

    def diff_remote(self, branch):
        logger.debug("Fetching from remote.")
        self.fetch()
        # Is `branch` actually a branch, a tag, or a commit? Heuristics:
        is_branch = branch in self.repo.remotes.origin.refs
        is_tag = branch in self.repo.tags
        maybe_commit = set(branch).issubset(string.hexdigits)
        logger.debug(
            "Branch %s --> is_branch: %s, is_tag: %s, maybe_commit: %s",
            branch,
            is_branch,
            is_tag,
            maybe_commit,
        )

        if not is_branch and not is_tag and not maybe_commit:
            logger.error("Branch %s does not exist at %s", branch, next(iter(self.repo.remotes.origin.urls)))
            raise BranchDoesNotExist(
                f"Please create branch '{branch}' in upstream and try again."
                f" If this is a new repo, please add a commit before syncing."
            )

        if is_branch:
            logger.debug("Getting diff between local branch and remote branch")
            diff = self.repo.git.diff("--name-status", f"origin/{branch}")
        else:
            logger.debug("Getting diff between local state and specified tag or commit")
            diff = self.repo.git.diff("--name-status", branch)

        if diff:  # if diff is not empty
            return convert_git_diff_log_to_list(diff)
        logger.debug("No Difference")
        return []
