#!/usr/bin/env python

import logging
import os
import os.path
import shutil
import tempfile

from git import Repo

logger = logging.getLogger(__name__)


SOURCE_DIR = os.path.join(os.path.dirname(__file__), "git_data")


def create_and_populate_git_repository(target_path):
    """Main entry point to this script."""
    os.makedirs(target_path, exist_ok=True)
    repo = Repo.init(target_path, initial_branch="main")
    repo.config_writer().set_value("user", "name", "Nautobot Automation").release()
    repo.config_writer().set_value("user", "email", "nautobot@nautobot.com").release()

    repo.index.commit("Empty commit")
    repo.create_tag("empty-repo", message="Nothing here yet")

    # Create a commit matching each subdirectory in the git_data directory
    for dirname in sorted(os.listdir(SOURCE_DIR)):
        # Clean up from any previous commit
        for root, _, files in os.walk(target_path):
            if ".git" in root:
                continue
            for filename in files:
                repo.index.remove([os.path.join(root, filename)])
                os.remove(os.path.join(root, filename))

        shutil.copytree(os.path.join(SOURCE_DIR, dirname), target_path, dirs_exist_ok=True)
        for root, _, files in os.walk(target_path):
            if ".git" in root:
                continue
            for filename in files:
                repo.index.add([os.path.join(root, filename)])
        repo.index.commit(dirname)
        # Directory "01-valid-files" --> tag "valid-files" so that we won't break tests if we renumber the directories
        repo.create_tag(dirname[3:], message=f"Tag based on {dirname} files")


if __name__ == "__main__":
    directory_path = tempfile.TemporaryDirectory().name  # pylint: disable=consider-using-with
    print(f"Creating test Git repository in {directory_path}...")
    create_and_populate_git_repository(directory_path)
