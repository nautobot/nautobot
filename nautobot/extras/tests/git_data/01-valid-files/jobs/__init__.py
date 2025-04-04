from nautobot.core.celery import register_jobs

from .my_job import MyJob, MyJobButtonReceiver, MyJobHookReceiver

register_jobs(MyJob, MyJobButtonReceiver, MyJobHookReceiver)
