import nautobot
from django.core.wsgi import get_wsgi_application

def on_startup(*, command, dirty):
    nautobot.setup()
    get_wsgi_application()
