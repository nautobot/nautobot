import sys

from celery.bin.celery import celery as celery_main
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Thin wrapper to the `celery` command that includes the Nautobot Celery
    app context. This allows us to execute Celery commands without having to
    worry about the chicken-and-egg problem with bootstrapping the Django
    settings.
    """

    def run_from_argv(self, argv):

        # The "celery" command uses Click, which directly relies upon
        # `sys.argv`. So we must explicitly remove "celery" from `sys.argv` so
        # that we can directly invoke Click ourselves, letting it work with the
        # args unhindered as if "celery" instead of "nautobot-server" were the
        # root command that was called from the CLI.
        sys.argv.remove("celery")

        celery_main.main()
