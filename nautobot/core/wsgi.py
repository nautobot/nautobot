import logging

from django.core import cache
from django.core.wsgi import get_wsgi_application
from django.db import connections

import nautobot

# This is the Django default left here for visibility on how the Nautobot pattern
# differs.
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nautobot.core.settings")

# Instead of importing `DJANGO_SETTINGS_MODULE` we're using the custom loader
# pattern from `nautobot.core.runner` to read environment or config path for us.
nautobot.setup()

# Use try/except because we might not be running uWSGI. If `settings.WEBSERVER_WARMUP` is `True`,
# will first call `get_internal_wsgi_application` which does not have `uwsgi` module loaded
# already. Therefore, `settings.WEBSERVER_WARMUP` to `False` for this code to be loaded.
try:
    import uwsgidecorators

    @uwsgidecorators.postfork
    def fix_uwsgi():
        import uwsgi

        logging.getLogger(__name__).info(
            f"Closing existing DB and cache connections on worker {uwsgi.worker_id()} after uWSGI forked ..."
        )
        connections.close_all()
        cache.close_caches()

except ImportError:
    pass

application = get_wsgi_application()
