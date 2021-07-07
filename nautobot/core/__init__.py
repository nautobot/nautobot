from nautobot.core import checks

# This will make sure the celery app is always imported when
# Django starts so that shared_task will use this app.
from nautobot.core.celery import app as celery_app

__all__ = ("celery_app",)
