from django_webserver.management.commands.pyuwsgi import Command as uWSGICommand


class Command(uWSGICommand):
    help = "Start Nautobot uWSGI server."
