from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from nautobot.extras.choices import JobExecutionType
from nautobot.extras.models import ScheduledJob


class Command(BaseCommand):
    help = "Remove stale scheduled jobs."

    def add_arguments(self, parser):
        parser.add_argument("max-age", type=int, help="Max age in days")

    def handle(self, *args, **options):
        ScheduledJob.objects.filter(start_time__lt=timezone.now() - timedelta(days=options["max-age"])).filter(
            Q(one_off=True) | ~Q(interval__in=JobExecutionType.RECURRING_CHOICES)
        ).delete()

        self.stdout.write(self.style.SUCCESS("Stale scheduled jobs deleted successfully"))
