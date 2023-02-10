# TODO: is this command still needed and relevant?
import os
import shutil
import subprocess

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Generate the nautobot ui javascript and css files and copy the index.html to templates/base.html"

    def handle(self, *args, **options):

        # generate nautobot_ui/src/router.js
        # TODO: does this have to happen on plugin load?

        # install npm dependencies and build compiled javascript
        ui_dir = os.path.join(os.path.dirname(settings.BASE_DIR), "nautobot_ui")
        npm_install = subprocess.run(["npm", "install"], cwd=ui_dir, check=False)
        if npm_install.returncode:
            raise CommandError(f"npm install failed with exit code {npm_install.returncode}")
        npm_build = subprocess.run(["npm", "run", "build"], cwd=ui_dir, check=False)
        if npm_build.returncode:
            raise CommandError(f"npm build failed with exit code {npm_build.returncode}")

        # copy nautobot_ui/build/index.html to nautobot/core/templates/base.html
        build_index_html = os.path.join(ui_dir, "build", "index.html")
        core_base_html = os.path.join(settings.BASE_DIR, "core", "templates", "base.html")
        shutil.copy2(build_index_html, core_base_html)
