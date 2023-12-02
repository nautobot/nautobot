#!/usr/bin/env bash

set -ex

git config --global --add safe.directory /source

# if [ ! -f ".git/hooks/pre-commit" ]; then
#     cd .git/hooks/
#     ln -s ../../scripts/git-hooks/pre-commit
# fi
