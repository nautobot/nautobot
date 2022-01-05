from nautobot.extras.plugins import PluginCustomValidator


class SiteCustomValidator(PluginCustomValidator):
    """
    Example of a PluginCustomValidator that checks if the name of a Site object is
    "this site has a matching name" and if so, raises a ValidationError.

    This is a trivial case used in testing and is constructed to only apply to a
    specific set of test cases, and not any others dealing with the Site model.
    """

    model = "dcim.site"

    def clean(self):
        """
        Apply custom model validation logic
        """
        obj = self.context["object"]
        if obj.name == "this site has a matching name":
            self.validation_error({"name": "Site name must be something valid"})


custom_validators = [SiteCustomValidator]
