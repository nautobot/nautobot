#!/usr/bin/env python

import json
import logging
import os
import os.path
import shutil
import sys
import tempfile

from git import Repo
import yaml


logger = logging.getLogger(__name__)


SOURCE_DIR = os.path.join(os.path.dirname(__file__), "git_data")



def create_and_populate_git_repository(directory_path):
    """Main entry point to this script."""
    os.makedirs(directory_path, exist_ok=True)
    repo = Repo.init(directory_path, initial_branch="main")
    repo.config_writer().set_value("user", "name", "Nautobot Automation").release()
    repo.config_writer().set_value("user", "email", "nautobot@nautobot.com").release()

    repo.index.commit("Empty commit")
    repo.create_tag("empty-repo", message="Nothing here yet")

    # Create a commit matching each subdirectory in the git_data directory
    for dirname in sorted(os.listdir(SOURCE_DIR)):
        # Clean up from any previous commit
        for root, dirs, files in os.walk(directory_path):
            if ".git" in root:
                continue
            for filename in files:
                repo.index.remove([os.path.join(root, filename)])
                os.remove(os.path.join(root, filename))

        shutil.copytree(os.path.join(SOURCE_DIR, dirname), directory_path, dirs_exist_ok=True)
        for root, dirs, files in os.walk(directory_path):
            if ".git" in root:
                continue
            for filename in files:
                repo.index.add([os.path.join(root, filename)])
        repo.index.commit(dirname)
        # Directory "01-valid-files" --> tag "valid-files" so that we won't break tests if we renumber the directories
        repo.create_tag(dirname[3:], message=f"Tag based on {dirname} files")


if __name__ == "__main__":
    directory_path = sys.argv[1] if len(sys.argv) == 2 else tempfile.TemporaryDirectory().name
    print(f"Creating test Git repository in {directory_path}...")
    create_and_populate_git_repository(directory_path)
