from nautobot.core.management.commands.shell import Command as _Command


class Command(_Command):
    """'nautobot-server nbshell' is a deprecated alias to 'nautobot-server shell'."""

    def get_imported_objects(self, options):
        """Import all app models and related code."""
        imported_objects = super().get_imported_objects(options)
        if not options.get("quiet_load"):
            self.stdout.write(
                self.style.WARNING(
                    "The 'nautobot-server nbshell' command is deprecated and will be removed in a future release."
                )
            )
            self.stdout.write(self.style.WARNING("Please use 'nautobot-server shell' instead."))
        return imported_objects
