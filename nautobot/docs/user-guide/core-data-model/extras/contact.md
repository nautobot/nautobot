# Contacts

A contact represents an individual that can be associated with other model instances. It stores the necessary information to uniquely identify and contact the individual. The information that can be stored on a contact includes the individual's name, phone number, email, and address. When a contact is assigned to an object, the status of such assignment needs to be specified.

A contact can be assigned to one or more [teams](team.md).

+/- 2.2.1

    A model can opt out of the ability to be associated with contacts or teams by specifying `is_contact_associable = False` in the model class definition. Note that presently this attribute only prevents contact/team related information from being displayed in the model UI and it does not actually prevent contacts/teams from associating to the model at the database level.

    ```python

    class YourModel(PrimaryModel):
        name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, db_index=True)
        is_contact_associable_model = False

        class Meta:
            abstract = True

    ```

+/- 2.3.0
    Models inheriting from `BaseModel` rather than `OrganizationalModel` or `PrimaryModel` now default to `is_contact_associable_model = False`. The `nautobot.apps.models.ContactMixin` mixin can be added to such models if desired.
