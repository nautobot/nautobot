import logging

from django.conf import settings
from django.core import cache
from django.core.wsgi import get_wsgi_application
from django.db import connections

import nautobot

logger = logging.getLogger(__name__)

# This is the Django default left here for visibility on how the Nautobot pattern
# differs.
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nautobot.core.settings")

# Instead of just pointing to `DJANGO_SETTINGS_MODULE` and letting Django run with it,
# we're using the custom Nautobot loader code to read environment or config path for us.
nautobot.setup()

# Use try/except because we might not be running uWSGI. If `settings.WEBSERVER_WARMUP` is `True`,
# will first call `get_internal_wsgi_application` which does not have `uwsgi` module loaded
# already. Therefore, `settings.WEBSERVER_WARMUP` to `False` for this code to be loaded.
try:
    import uwsgidecorators

    @uwsgidecorators.postfork
    def fix_uwsgi():
        import uwsgi

        logger.info("Closing existing DB and cache connections on worker %s after uWSGI forked ...", uwsgi.worker_id())
        connections.close_all()
        cache.close_caches()

        # Create the OpenTelemetry OTLP exporters here, in the forked worker, rather than in the
        # pre-fork master. The OTLP gRPC exporter's channel spins up fork-unsafe C-core threads/fds
        # at construction; if built in the master they are inherited broken by workers and segfault
        # when a request is exported (aggravated by django-silk cProfile). instrument() deliberately
        # skips exporter creation for this reason; install_exporters() is idempotent.
        if settings.OTEL_PYTHON_DJANGO_INSTRUMENT:
            from nautobot.core.cli.opentelemetry import install_exporters

            install_exporters()

except ImportError:
    pass

application = get_wsgi_application()
