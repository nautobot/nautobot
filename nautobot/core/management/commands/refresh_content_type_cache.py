from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand

from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    help = "Update the cached content type for all model classes."

    def handle(self, *args, **kwargs):
        """Run through all ContentTypes and ensure their associated models have the correctly cached content type."""

        if settings.CONTENT_TYPE_CACHE_TIMEOUT == 0:
            self.stdout.write(self.style.NOTICE("CONTENT_TYPE_CACHE_TIMEOUT is set to 0; skipping cache refresh"))
            return

        content_types = ContentType.objects.all()

        for content_type in content_types:
            self.stdout.write(self.style.SUCCESS(f"Processing {content_type}"))
            cache_key = f"{content_type.model_class()._meta.label_lower}.content_type"

            cache.set(cache_key, content_type, settings.CONTENT_TYPE_CACHE_TIMEOUT)
