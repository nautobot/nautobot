#!/usr/bin/env python

import logging
import os
import os.path
import shutil
import tempfile

from git import Repo

logger = logging.getLogger(__name__)


SOURCE_DIR = os.path.join(os.path.dirname(__file__), "git_data")


def create_and_populate_git_repository(target_path, divergent_branch=None):
    """
    Create a Git repository in `target_path` and populate it with commits and tags based on contents of `SOURCE_DIR`.

    An initial commit will always be created, containing no tracked files, and will be given the tag `empty-repo`.
    After that, each subdir under `SOURCE_DIR` will be used as the basis for a single commit to the repo, so given:

        nautobot/extras/tests/git_data
        ├── 01-valid-files
        │   ├── config_context_schemas
        │   │   └── schema-1.yaml
        │   └── config_contexts
        │       └── context.yaml
        └── 02-invalid-files
            └── config_context_schemas
             ├── badschema1.json
             └── badschema2.json

    ...after the initial empty commit, the next commit would contain files `config_context_schemas/schema-1.yaml` and
    `config_contexts/context.yaml`, and would be given the tag `valid-files`. The next commit would remove those files
    but add the files `config_context_schemas/badschema1.json` and `config_context_schemas/badschema2.json`, and would
    be tagged as `invalid-files`.

    Note that each commit is fully defined by the files in the appropriate subdirectory; if you want a file to exist
    across multiple separate commits, it must exist in multiple subdirectories. Use of symlinks is encouraged in such
    a scenario.

    You can optionally create and check out a divergent branch from the main branch by passing a branch name as the `divergent_branch`.
    This will write a commit to the divergent branch and tag it with the branch name with the `-tag` suffix.
    """
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

    if divergent_branch:
        repo.create_head(divergent_branch)
        repo.index.commit("divergent-branch")
        repo.create_tag(f"{divergent_branch}-tag", message=f"Tag for divergent branch {divergent_branch}")


if __name__ == "__main__":
    directory_path = tempfile.TemporaryDirectory().name  # pylint: disable=consider-using-with
    print(f"Creating test Git repository in {directory_path}...")
    create_and_populate_git_repository(directory_path)
