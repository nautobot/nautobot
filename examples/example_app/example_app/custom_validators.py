from nautobot.apps.models import CustomValidator


class LocationCustomValidator(CustomValidator):
    """
    Example of a CustomValidator that checks if the name of a Location object is
    "this location has a matching name" and if so, raises a ValidationError.

    This is a trivial case used in testing and is constructed to only apply to a
    specific set of test cases, and not any others dealing with the Location model.
    """

    model = "dcim.location"

    def clean(self):
        """
        Apply custom model validation logic
        """
        obj = self.context["object"]
        if obj.name == "this location has a matching name":
            self.validation_error({"name": "Location name must be something valid"})


class RelationshipAssociationCustomValidator(CustomValidator):
    model = "extras.relationshipassociation"

    def clean(self):
        """
        Custom validator for RelationshipAssociation to enforce that an IP Address(destination) must be
        within the host range of a Prefix(source)
        """
        obj = self.context["object"]
        if obj.relationship.key != "test_relationship":
            # Not a relationship we have an interest in validating
            return
        prefix_host_range = obj.source.prefix.iter_hosts()
        if obj.destination.address.ip not in prefix_host_range:
            self.validation_error(
                {"address": "Gateway IP is not a valid IP inside the host range of the defined prefix"}
            )


custom_validators = [LocationCustomValidator, RelationshipAssociationCustomValidator]
