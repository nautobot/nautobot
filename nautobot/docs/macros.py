"""mkdocs-macros-plugin data loading etc."""

import os.path

import yaml


def define_env(env):
    # Are we seeing ourselves as in `./docs/` or in `./nautobot/docs/`?
    if os.path.basename(os.path.dirname(os.path.dirname(__file__))) == "nautobot":
        settings_file = os.path.join(os.path.dirname(__file__), "..", "core", "settings.yaml")
    else:
        settings_file = os.path.join(os.path.dirname(__file__), "..", "nautobot", "core", "settings.yaml")
    with open(settings_file, "rt") as fh:
        env.variables["settings_data"] = yaml.safe_load(fh)
