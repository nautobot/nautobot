from nautobot.apps.jobs import register_jobs

from .jobs_submodule import ChildJob

register_jobs(ChildJob)
