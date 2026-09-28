from django.contrib.messages.storage.fallback import FallbackStorage


class NautobotMessageStorage(FallbackStorage):
    def add(self, level, message, extra_tags=""):
        """
        Queue a message to be stored.

        We add custom logic to avoid storing duplicate message entries.
        """
        # Iterating self sets `self.used = True` which has downstream consequences, so restore it to its previous value
        used = self.used
        if any(msg.level == level and msg.message == message for msg in self):
            # Duplicate message, don't bother to store it
            self.used = used
            return
        self.used = used
        super().add(level, message, extra_tags=extra_tags)
