from django.core.management.base import BaseCommand

from nautobot.dcim.models import Location
from nautobot.extras.filters import ContactFilterSet, TeamFilterSet


class Command(BaseCommand):
    help = "Migrate Location contact fields to Contact and Team objects."

    def handle(self, *args, **kwargs):
        """Iterate through Locations with contact information and try to match to existing Contact or Team."""
        locations_with_contact_data = Location.objects.exclude(
            physical_address__isnull=True,
            shipping_address__isnull=True,
            contact_name__isnull=True,
            contact_phone__isnull=True,
            contact_email__isnull=True,
        )
        for location in locations_with_contact_data:
            print(f"Finding existing Contacts or Teams for location {location}...")
            similar_contacts = ContactFilterSet(data={"similar_to_location_data": [location]}).qs
            similar_teams = TeamFilterSet(data={"similar_to_location_data": [location]}).qs

            if similar_contacts.exists() or similar_teams.exists():
                print(f"Found similar contacts for location {location}:")
                for i, contact in enumerate(similar_contacts):
                    print(f"c{i}: {contact}")
                for i, team in enumerate(similar_teams):
                    print(f"t{i}: {team}")
                print("n: Create a new Contact or Team")
                choice = input("Select a choice from the list of items: ")
                if choice == "n":
                    print("TODO: Creating a new Contact or Team...")
                    continue
                elif choice.lower().startswith("c"):
                    contact = similar_contacts[int(choice[1:])]
                    location.contacts.add(contact)
                    print(f"Set location {location} contact to {contact}")
                elif choice.lower().startswith("t"):
                    team = similar_teams[int(choice[1:])]
                    location.contacts.add(team)
                    print(f"Set location {location} contact to {team}")
