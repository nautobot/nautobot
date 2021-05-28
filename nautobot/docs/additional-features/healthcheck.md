# Healthcheck Endpoint

Nautobot includes a health check endpoint `/health` which utilizes the [django-health-check](https://github.com/KristianOellegaard/django-health-check) project.  This endpoint is designed for use by an optional load balancer placed in front of Nautobot to determine the health of the Nautobot server.  By default the healthcheck enables checks for the following:

* Database Backend
* Caching Backend
* Storage Backend

Additional health checks are available as part of the [django-health-check](https://github.com/KristianOellegaard/django-health-check) project and can be added to the [`EXTRA_INSTALLED_APPS`](../configuration/optional-settings.md#extra-applications) configuration variable as desired.  The Nautobot server is healthy if the HTTP response is 200 from a GET request to `/health`, a web UI is also available at the same endpoint for human consumption.
