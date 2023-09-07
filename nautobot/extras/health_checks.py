"""Nautobot custom health checks."""
from typing import Optional
from urllib.parse import urlparse

from django.conf import settings
from django.db import DatabaseError, IntegrityError, connection
from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import ServiceReturnedUnexpectedResult, ServiceUnavailable
from prometheus_client import Gauge
from redis import exceptions, from_url
from redis.client import Redis
from redis.sentinel import Sentinel

from .models import HealthCheckTestModel


class NautobotHealthCheckBackend(BaseHealthCheckBackend):
    """Automatically set metric based on the outcome of the check.

    Due to the multiprocess nature of Nautobot we have multiple processes generating health check metrics. Most of these
    seem to never run the health checks and therefore the value stays at the uninitiated value of -1. Therefore, we set
    'multiprocess_mode' to "max", as the values 0 (down) or 1 (up) are always bigger than -1. Finally, we use a gauge
    metric instead of the more intuitive enum, because the latter doesn't support multiprocessing.
    """

    MULTIPROCESS_MODE = "max"

    states = {"unknown": -1, "down": 0, "up": 1}
    metric: Optional[Gauge] = None  # Set this in subclasses

    def __init__(self):
        super().__init__()
        # Initialize the metric as -1 if present
        if self.metric:
            self.metric.set(self.states["unknown"])

    def run_check(self):
        super().run_check()
        if not self.metric:
            return
        if self.errors:
            self.metric.set(self.states["down"])
        else:
            self.metric.set(self.states["up"])


class DatabaseBackend(NautobotHealthCheckBackend):
    """Check database connectivity, test read/write if available."""

    metric = Gauge(
        "health_check_database_info",
        "State of database backend",
        multiprocess_mode=NautobotHealthCheckBackend.MULTIPROCESS_MODE,
    )

    def check_status(self):
        """Check the database connection is available."""
        try:
            if settings.MAINTENANCE_MODE:
                # Check DB for read access only
                connection.ensure_connection()
            else:
                # Check DB for read/write access
                obj = HealthCheckTestModel.objects.create(title="test")
                obj.title = "newtest"
                obj.save()
                obj.delete()
        except IntegrityError:
            raise ServiceReturnedUnexpectedResult("Integrity Error")
        except DatabaseError:
            raise ServiceUnavailable("Database error")


class RedisHealthCheck(NautobotHealthCheckBackend):
    def check_sentinel(self, sentinel_servers, service_name, db, **kwargs):
        try:
            sentinel = Sentinel(
                sentinel_servers,
                **kwargs,
            )
            with sentinel.master_for(service_name=service_name, db=db) as master:
                master.ping()
        except (ConnectionRefusedError, exceptions.ConnectionError, exceptions.TimeoutError) as e:
            self.add_error(ServiceUnavailable(f"Unable to connect to Redis Sentinel: {type(e).__name__}"), e)
        except Exception as e:
            self.add_error(ServiceUnavailable("Unknown error"), e)

    def check_redis(self, redis_url=None, **kwargs):
        try:
            if redis_url:
                with from_url(redis_url, **kwargs) as conn:
                    conn.ping()  # exceptions may be raised upon ping
            else:
                with Redis(**kwargs) as conn:
                    conn.ping()  # exceptions may be raised upon ping
        except (ConnectionRefusedError, exceptions.ConnectionError, exceptions.TimeoutError) as e:
            self.add_error(ServiceUnavailable(f"Unable to connect to Redis: {type(e).__name__}"), e)
        except Exception as e:
            self.add_error(ServiceUnavailable("Unknown error"), e)


class RedisBackend(RedisHealthCheck):
    """Health check for Django Redis."""

    metric = Gauge(
        "health_check_redis_backend_info",
        "State of redis backend",
        multiprocess_mode=NautobotHealthCheckBackend.MULTIPROCESS_MODE,
    )

    caches = getattr(settings, "CACHES", {}).get("default", {})

    def check_status(self):
        """Check Redis service by pinging the redis instance with a redis connection."""
        # if Sentinel is enabled we need to check Redis using Sentinel
        options = self.caches.get("OPTIONS", {})
        client_class = options.get("CLIENT_CLASS", "")
        location = self.caches.get("LOCATION", None)
        if location is None:
            self.add_error(ServiceUnavailable("LOCATION is not set"))
        if client_class == "django_redis.client.SentinelClient":
            redis_url = urlparse(location)
            service_name = redis_url.netloc
            db = int(redis_url.path.replace("/", ""))
            remaining_args = {
                "password": options.get("PASSWORD", ""),
                "socket_timeout": options.get("SOCKET_TIMEOUT", None),
                "socket_connect_timeout": options.get("SOCKET_CONNECT_TIMEOUT", None),
                "sentinel_kwargs": options.get("SENTINEL_KWARGS", {}),
                **options.get("CONNECTION_POOL_KWARGS", {}),
            }
            self.check_sentinel(
                sentinel_servers=options.get("SENTINELS"), service_name=service_name, db=db, **remaining_args
            )
        # Sentinel is not used, so we check Redis directly
        elif client_class == "django_redis.client.DefaultClient":
            self.check_redis(redis_url=location, **options.get("CONNECTION_POOL_KWARGS", {}))
        else:
            if self.redis_url is None:
                self.add_error(ServiceUnavailable(f"{client_class} is an unsupported CLIENT_CLASS!"))
