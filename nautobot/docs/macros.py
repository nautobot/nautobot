"""mkdocs-macros-plugin data loading etc."""

import os.path

import yaml


def define_env(env):
    """Load nautobot/core/*.yaml source-of-truth files into the Jinja2 rendering environment."""
    core_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nautobot", "core")

    with open(os.path.join(core_dir, "settings.yaml"), "rt") as fh:
        env.variables["settings_schema"] = yaml.safe_load(fh)

    with open(os.path.join(core_dir, "searchable_fields.yaml"), "rt") as fh:
        env.variables["searchable_fields"] = yaml.safe_load(fh)
