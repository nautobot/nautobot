"""mkdocs-macros-plugin data loading etc."""

import yaml
import os.path


def define_env(env):
    with open(os.path.join(os.path.dirname(__file__), "..", "core", "settings.yaml"), "rt") as fh:
        env.variables["settings_data"] = yaml.safe_load(fh)
