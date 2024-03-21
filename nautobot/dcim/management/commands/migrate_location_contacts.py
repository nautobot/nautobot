from django.core.management.base import BaseCommand
from django.db import transaction

from nautobot.dcim.models import Location
from nautobot.extras.filters import ContactFilterSet, TeamFilterSet
from nautobot.extras.models import Contact, ContactAssociation, Role, Status, Team


class Command(BaseCommand):
    help = "Migrate Location contact fields to Contact and Team objects."

    def handle(self, *args, **kwargs):
        try:
            with transaction.atomic():
                self.migrate_location_contacts()
        # TODO: on keyboardinterrupt, ask the user if they want to roll back
        except KeyboardInterrupt:
            self.stdout.write(self.style.ERROR("\nMigration cancelled, all changes rolled back."))
        except:
            self.stdout.write(self.style.ERROR("\nMigration failed, all changes rolled back."))
            raise

    def migrate_location_contacts(self):
        """Iterate through Locations with contact information and try to match to existing Contact or Team."""
        locations_with_contact_data = Location.objects.exclude(
            physical_address__isnull=True,
            shipping_address__isnull=True,
            contact_name__isnull=True,
            contact_phone__isnull=True,
            contact_email__isnull=True,
        )
        for location in locations_with_contact_data:
            self.stdout.write(f"Finding existing Contacts or Teams for location {location}...")
            similar_contacts = list(ContactFilterSet(data={"similar_to_location_data": [location]}).qs)
            similar_teams = list(TeamFilterSet(data={"similar_to_location_data": [location]}).qs)

            if not any([similar_contacts, similar_teams]):
                continue

            # Found similar contacts or teams, prompt user for action
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(f"Found similar contacts/teams for location {location.display}:"))
            self.stdout.write(f"    current contact name: {location.contact_name!r}")
            self.stdout.write(f"    current contact phone: {location.contact_phone!r}")
            self.stdout.write(f"    current contact email: {location.contact_email!r}")
            self.stdout.write(f"    current physical address: {location.physical_address!r}")
            self.stdout.write(f"    current shipping address: {location.shipping_address!r}")
            self.stdout.write("")

            # Output menu of choices of valid contacts/teams
            for i, contact in enumerate(similar_contacts):
                self.stdout.write(self.style.WARNING(f"c{i}") + f": {contact}")
            for i, team in enumerate(similar_teams):
                self.stdout.write(self.style.WARNING(f"t{i}") + f": {team}")
            self.stdout.write(self.style.WARNING("n") + ": Create a new Contact or Team")
            self.stdout.write(self.style.WARNING("s") + ": Skip this location")

            # Retrieve desired contact/team from user input
            selected_contact = None
            while True:
                choice = input("Select a choice from the list of items: ")
                if choice == "s":
                    self.stdout.write(f"Skipping location {location}")
                    break
                elif choice == "n":
                    self.stdout.write("TODO: Creating a new Contact or Team...")
                    break
                elif choice.lower().startswith("c") and int(choice[1:]) < len(similar_contacts):
                    selected_contact = similar_contacts[int(choice[1:])]
                    break
                elif choice.lower().startswith("t") and int(choice[1:]) < len(similar_teams):
                    selected_contact = similar_teams[int(choice[1:])]
                    break

            if selected_contact is None:
                continue

            # Prompt for role
            self.stdout.write("\nValid roles for this association:")
            valid_roles = list(Role.objects.get_for_model(ContactAssociation))
            for i, role in enumerate(valid_roles):
                self.stdout.write(self.style.WARNING(f"{i}") + f": {role}")
            while True:
                selected_role = input("Select a role for this association: ")
                if int(selected_role) < len(valid_roles):
                    role = valid_roles[int(selected_role)]
                    break

            # Prompt for status
            self.stdout.write("\nValid statuses for this association:")
            valid_statuses = list(Status.objects.get_for_model(ContactAssociation))
            for i, status in enumerate(valid_statuses):
                self.stdout.write(self.style.WARNING(f"{i}") + f": {status}")
            while True:
                selected_status = input("Select a status for this association: ")
                if int(selected_status) < len(valid_statuses):
                    status = valid_statuses[int(selected_status)]
                    break

            # Create the association
            # TODO: clear out existing contact data
            # TODO: email match should be exact (case insensitive?)
            try:
                contact_association = ContactAssociation(
                    contact=selected_contact if isinstance(selected_contact, Contact) else None,
                    team=selected_contact if isinstance(selected_contact, Team) else None,
                    associated_object=location,
                    role=role,
                    status=status,
                )
                contact_association.validated_save()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to create association: {e}"))
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"Associated contact/team {selected_contact} to location {location}")
                )
