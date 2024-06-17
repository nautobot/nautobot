from nautobot.core.celery import register_jobs

from .my_job import MyJob

register_jobs(MyJob)
