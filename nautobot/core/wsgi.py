from django.core.wsgi import get_wsgi_application

import nautobot

# This is the Django default left here for visibility on how the Nautobot pattern
# differs.
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nautobot.core.settings")

# Instead of importing `DJANGO_SETTINGS_MODULE` we're using the custom loader
# pattern from `nautobot.core.runner` to read environment or config path for us.
nautobot.setup()

application = get_wsgi_application()
