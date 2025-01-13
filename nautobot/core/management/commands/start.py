from django_webserver.management.commands.pyuwsgi import Command as uWSGICommand  # type: ignore[import-untyped]


class Command(uWSGICommand):
    help = "Start Nautobot uWSGI server."
