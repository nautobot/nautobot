"""mkdocs-macros-plugin data loading etc."""

import os.path

import yaml


def define_env(env):
    """Load nautobot/core/settings.yaml into the Jinja2 rendering environment."""
    settings_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nautobot", "core", "settings.yaml"
    )
    with open(settings_file, "rt") as fh:
        env.variables["settings_schema"] = yaml.safe_load(fh)
