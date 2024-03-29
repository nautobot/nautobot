from textwrap import dedent, indent

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction

from nautobot.dcim.models import Location
from nautobot.extras.filters import ContactFilterSet, TeamFilterSet
from nautobot.extras.models import Contact, ContactAssociation, Role, Status, Team


class Command(BaseCommand):
    help = "Migrate Location contact fields to Contact and Team objects."
    verbose_help = """
    This command will present a series of prompts to guide you through migrating Locations that
    have data in the `contact_name`, `contact_phone`, or `contact_email` fields which are not
    already associated to a Contact or Team. This command will give you the option to create new
    Contacts or Teams or, if a similar Contact or Team already exists, to link the Location to the
    existing Contact or Team. Note that when assigning a Location to an existing Contact or Team
    that has a blank `phone` or `email` field, the value from the Location will be copied to the
    Contact/Team. After a Location has been associated to a Contact or Team, the `contact_name`,
    `contact_phone`, and `contact_email` fields will be cleared from the Location.
    """

    def handle(self, *args, **kwargs):
        status_role_err_msg = "No {0} found for the ContactAssociation content type. Please ensure {0} are created before running this command."
        if not Status.objects.get_for_model(ContactAssociation).exists():
            self.stdout.write(self.style.ERROR(status_role_err_msg.format("statuses")))
            return
        if not Role.objects.get_for_model(ContactAssociation).exists():
            self.stdout.write(self.style.ERROR(status_role_err_msg.format("roles")))
            return

        self.stdout.write(self.style.NOTICE(" ".join(dedent(self.verbose_help).split("\n"))))

        try:
            with transaction.atomic():
                try:
                    self.migrate_location_contacts()
                except KeyboardInterrupt:
                    while True:
                        rollback = input("\nRoll back changes? [y/n]: ").strip().lower()
                        if rollback == "y":
                            raise
                        elif rollback == "n":
                            break
        except KeyboardInterrupt:
            self.stdout.write(self.style.ERROR("\nOperation cancelled, all changes rolled back."))
        except:
            self.stdout.write(self.style.ERROR("\nOperation failed, all changes rolled back."))
            raise

    def migrate_location_contacts(self):
        """Iterate through Locations with contact information and try to match to existing Contact or Team."""
        locations_with_contact_data = (
            Location.objects.without_tree_fields()
            .exclude(
                contact_name="",
                contact_phone="",
                contact_email="",
            )
            .filter(associated_contacts__isnull=True)
        )

        for location in locations_with_contact_data:
            self.stdout.write(f"Finding existing Contacts or Teams for location {location.display}...")
            selected_contact = None
            similar_contacts = list(ContactFilterSet(data={"similar_to_location_data": [location]}).qs)
            similar_teams = list(TeamFilterSet(data={"similar_to_location_data": [location]}).qs)
            similar_contacts_and_teams = similar_contacts + similar_teams

            if not similar_contacts_and_teams:
                self.stdout.write(
                    self.style.WARNING(f"No similar Contacts or Teams found for location {location.display}.")
                )

            else:
                # Found similar contacts or teams, prompt user for action
                self.stdout.write("")
                self.stdout.write(self.style.WARNING(f"Found similar contacts/teams for location {location.display}:"))
                self.stdout.write(f"    current contact name: {location.contact_name!r}")
                self.stdout.write(f"    current contact phone: {location.contact_phone!r}")
                self.stdout.write(f"    current contact email: {location.contact_email!r}")
                self.stdout.write("")

                # Output menu of choices of valid contacts/teams
                for i, contact in enumerate(similar_contacts_and_teams, start=1):
                    self.stdout.write(f"{self.style.WARNING(i)}: {contact._meta.model_name.title()}: {contact.name}")
                    self.print_contact_fields(contact, rjust=len(str(i)) + len(contact._meta.model_name) + 2)
                    self.stdout.write("")

            self.stdout.write(self.style.WARNING("c") + ": Create a new Contact")
            self.stdout.write(self.style.WARNING("t") + ": Create a new Team")
            self.stdout.write(self.style.WARNING("s") + ": Skip this location")

            # Retrieve desired contact/team from user input
            while True:
                choice = input("Select a choice from the list of items: ")
                if choice == "s":
                    self.stdout.write(f"Skipping location {location.display}")
                    break
                elif choice == "c":
                    selected_contact = self.create_new_contact_from_location(location, model=Contact)
                    break
                elif choice == "t":
                    selected_contact = self.create_new_contact_from_location(location, model=Team)
                    break
                elif choice.lower() == "q":
                    raise KeyboardInterrupt
                elif choice.isdigit() and 0 < int(choice) <= len(similar_contacts_and_teams):
                    selected_contact = similar_contacts_and_teams[int(choice) - 1]
                    break

            if selected_contact is not None:
                self.associate_contact_to_location(selected_contact, location)

    def associate_contact_to_location(self, contact, location):
        role, status = self.prompt_for_role_and_status()

        # If email or phone fields are present in the location but not the contact, update the contact fields
        updated_fields = {}
        if location.contact_phone and not contact.phone:
            contact.phone = location.contact_phone
            updated_fields["phone"] = location.contact_phone
        if location.contact_email and not contact.email:
            contact.email = location.contact_email
            updated_fields["email"] = location.contact_email
        if updated_fields:
            try:
                contact.validated_save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Updated {contact._meta.model_name.title()} {contact.name} field(s): {updated_fields!r}"
                    )
                )
            except ValidationError as e:
                contact.refresh_from_db()
                self.stdout.write(
                    self.style.ERROR(f"Attempted to update {contact!r} field(s) but failed: {updated_fields!r}: {e}")
                )

        try:
            contact_association = ContactAssociation(
                contact=contact if isinstance(contact, Contact) else None,
                team=contact if isinstance(contact, Team) else None,
                associated_object=location,
                role=role,
                status=status,
            )
            contact_association.validated_save()
            location.contact_name = ""
            location.contact_email = ""
            location.contact_phone = ""
            location.validated_save()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to create association: {e}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Associated {contact!r} to location {location.display}"))

    def prompt_for_role_and_status(self):
        # Prompt for role
        self.stdout.write("\nValid roles for this association:")
        valid_roles = list(Role.objects.get_for_model(ContactAssociation))
        for i, role in enumerate(valid_roles, start=1):
            self.stdout.write(self.style.WARNING(f"{i}") + f": {role}")
        while True:
            selected_role = input("Select a role for this association: ")
            if selected_role.isdigit() and 0 < int(selected_role) <= len(valid_roles):
                role = valid_roles[int(selected_role) - 1]
                break

        # Prompt for status
        self.stdout.write("\nValid statuses for this association:")
        valid_statuses = list(Status.objects.get_for_model(ContactAssociation))
        for i, status in enumerate(valid_statuses, start=1):
            self.stdout.write(self.style.WARNING(f"{i}") + f": {status}")
        while True:
            selected_status = input("Select a status for this association: ")
            if selected_status.isdigit() and 0 < int(selected_status) <= len(valid_statuses):
                status = valid_statuses[int(selected_status) - 1]
                break

        return role, status

    def create_new_contact_from_location(self, location, model):
        """Create a new Contact or Team from the location's contact data."""

        self.stdout.write(f"Creating new {model._meta.model_name.title()} for location {location.display}...")
        name = location.contact_name
        phone = location.contact_phone
        email = location.contact_email
        self.stdout.write(f"    contact name: {name!r}")
        self.stdout.write(f"    contact phone: {phone!r}")
        self.stdout.write(f"    contact email: {email!r}")

        while not name:
            name = input(f"Name is required. Enter a name for the new {model._meta.model_name.title()}: ")

        try:
            contact = model(
                name=name,
                phone=phone,
                email=email,
            )
            contact.validated_save()
            return contact
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to create {model._meta.model_name.title()}: {e}"))
            return None

    def print_contact_fields(self, contact, rjust=0):
        for field_name in ["phone", "email"]:
            if getattr(contact, field_name):
                self.stdout.write(
                    field_name.title().rjust(rjust)
                    + ": "
                    + indent(getattr(contact, field_name), " " * (rjust + 2)).lstrip()
                )
