from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Update the cached content type for all model classes."

    def handle(self, *args, **kwargs):
        """Run through all ContentTypes and ensure their associated models have the correctly cached content type."""

        if settings.CONTENT_TYPE_CACHE_TIMEOUT == 0:
            self.stdout.write(self.style.NOTICE("CONTENT_TYPE_CACHE_TIMEOUT is set to 0; skipping cache refresh"))
        else:
            self.stdout.write(self.style.NOTICE("Refreshing content type cache"))

        content_types = ContentType.objects.all()

        for content_type in content_types:
            try:
                if settings.CONTENT_TYPE_CACHE_TIMEOUT == 0:
                    cache.delete(content_type.model_class()._content_type_cache_key)
                else:
                    cache.set(
                        content_type.model_class()._content_type_cache_key,
                        content_type,
                        settings.CONTENT_TYPE_CACHE_TIMEOUT,
                    )

            except AttributeError:
                pass
