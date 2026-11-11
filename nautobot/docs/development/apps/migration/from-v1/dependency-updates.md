# Dependency Updates

## Nautobot Version

Change your Nautobot to the latest/v2.0 release.

## Python Version

Python 3.9 support is dropped as of Nautobot v2.4.20.

Python 3.10 support is dropped as of Nautobot v2.4.46.

Python 3.11 is the current minimum version for later versions of Nautobot 2.4.x and compatible apps.

## `pylint-nautobot`

`pylint-nautobot` is now a required dev-dependency. Make sure you add `pylint-nautobot = "*"` under `tool.poetry.dev-dependencies` section in your `pyproject.toml`.
