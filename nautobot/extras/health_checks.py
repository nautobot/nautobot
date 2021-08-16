"""Nautobot custom health checks."""
from django.conf import settings
from django.db import DatabaseError, IntegrityError, connection
from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import ServiceReturnedUnexpectedResult, ServiceUnavailable

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
