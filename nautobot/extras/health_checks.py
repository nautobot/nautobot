"""Nautobot custom health checks."""
from django.conf import settings
from django.db import DatabaseError, IntegrityError, connection
from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import ServiceReturnedUnexpectedResult, ServiceUnavailable
from redis import exceptions, from_url
from redis.sentinel import Sentinel

from .models import HealthCheckTestModel


class DatabaseBackend(BaseHealthCheckBackend):
    """Check database connectivity, test read/write if available."""

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


class RedisBackend(BaseHealthCheckBackend):
    """Health check for Redis."""

    redis_url = getattr(settings, "CACHEOPS_REDIS", None)
    sentinel_url = getattr(settings, "CACHEOPS_SENTINEL", None)

    def check_status(self):
        """Check Redis service by pinging the redis instance with a redis connection."""
        # if Sentinel is enabled we need to check Redis using Sentinel
        if self.sentinel_url is not None:
            try:
                sentinel = Sentinel(
                    self.sentinel_url["locations"],
                    password=self.sentinel_url.get("password", None),
                    sentinel_kwargs=self.sentinel_url.get("sentinel_kwargs", None),
                    socket_timeout=self.sentinel_url.get("socket_timeout", None),
                )
                with sentinel.master_for(self.sentinel_url["service_name"], db=self.sentinel_url["db"]) as master:
                    master.ping()
            except (ConnectionRefusedError, exceptions.ConnectionError, exceptions.TimeoutError) as e:
                self.add_error(ServiceUnavailable("Unable to connect to Redis Sentinel: %s" % type(e).__name__), e)
            except Exception as e:
                self.add_error(ServiceUnavailable("Unknown error"), e)
        # Sentinel is not used, so we check Redis directly
        else:
            if self.redis_url is None:
                self.add_error(ServiceUnavailable("CACHEOPS_REDIS is not set"))
            else:
                try:
                    # conn is used as a context to release opened resources later
                    with from_url(self.redis_url) as conn:
                        conn.ping()  # exceptions may be raised upon ping
                except (ConnectionRefusedError, exceptions.ConnectionError, exceptions.TimeoutError) as e:
                    self.add_error(ServiceUnavailable("Unable to connect to Redis: %s" % type(e).__name__), e)
                except Exception as e:
                    self.add_error(ServiceUnavailable("Unknown error"), e)
