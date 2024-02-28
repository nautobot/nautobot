"""mkdocs-macros-plugin data loading etc."""

import json
import os.path


def define_env(env):
    with open(os.path.join(os.path.dirname(__file__), "..", "core", "settings.json"), "rt") as fh:
        env.variables["settings_data"] = json.load(fh)
