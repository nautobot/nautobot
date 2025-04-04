#!/usr/bin/env bash

set -ex

# Make sure port defintion is written to disk
poetry run invoke vscode --no-workspace-launch
