from nautobot.core.celery import register_jobs

from .cleanup import FixIPAMParents

name = "System Jobs"

jobs = [
    FixIPAMParents,
]
register_jobs(*jobs)
