# Dependency Updates

## Nautobot Version

Change your Nautobot to the latest/v2.0 release.

## Python Version

Python 3.8 support is dropped for Nautobot v2.4 and Python 3.9.2 is the minimum version for Nautobot and its apps.

## `pylint-nautobot`

`pylint-nautobot` is now a required dev-dependency. Make sure you add `pylint-nautobot = "*"` under `tool.poetry.dev-dependencies` section in your `pyproject.toml`.
