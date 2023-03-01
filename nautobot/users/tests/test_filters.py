import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import make_aware

from nautobot.users.filters import (
    GroupFilterSet,
    ObjectPermissionFilterSet,
    TokenFilterSet,
    UserFilterSet,
)
from nautobot.users.models import ObjectPermission, Token
from nautobot.utilities.testing import FilterTestCases
import netaddr
from nautobot.dcim.choices import (
    CableLengthUnitChoices,
    CableTypeChoices,
    DeviceFaceChoices,
    InterfaceModeChoices,
    InterfaceTypeChoices,
    PortTypeChoices,
    PowerFeedPhaseChoices,
    PowerFeedSupplyChoices,
    PowerFeedTypeChoices,
    PowerOutletFeedLegChoices,
    RackDimensionUnitChoices,
    RackTypeChoices,
    RackWidthChoices,
    SubdeviceRoleChoices,
)

from nautobot.dcim.models import (
    Cable,
    ConsolePort,
    ConsolePortTemplate,
    ConsoleServerPort,
    ConsoleServerPortTemplate,
    Device,
    DeviceBay,
    DeviceBayTemplate,
    DeviceRedundancyGroup,
    DeviceRole,
    DeviceType,
    FrontPort,
    FrontPortTemplate,
    Interface,
    InterfaceTemplate,
    InventoryItem,
    Location,
    LocationType,
    Manufacturer,
    Platform,
    PowerFeed,
    PowerPanel,
    PowerPort,
    PowerPortTemplate,
    PowerOutlet,
    PowerOutletTemplate,
    Rack,
    RackGroup,
    RackReservation,
    RackRole,
    RearPort,
    RearPortTemplate,
    Region,
    Site,
    VirtualChassis,
)

from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider
from nautobot.extras.models import SecretsGroup, Status
from nautobot.ipam.models import IPAddress, Prefix, Service, VLAN, VLANGroup
from nautobot.tenancy.models import Tenant
from nautobot.utilities.testing import FilterTestCases
from nautobot.utilities.utils import flatten_iterable
from nautobot.virtualization.models import Cluster, ClusterType, VirtualMachine

# Use the proper swappable User model
User = get_user_model()


def common_test_data(cls):
    pass

    # users = (
    #     User.objects.create_user(username="TestCaseUser 1"),
    #     User.objects.create_user(username="TestCaseUser 2"),
    #     User.objects.create_user(username="TestCaseUser 3"),
    # )


class UserTestCase(FilterTestCases.FilterTestCase):
    queryset = User.objects.all()
    filterset = UserFilterSet

    @classmethod
    def setUpTestData(cls):
        groups = (
            Group.objects.create(name="Group 1"),
            Group.objects.create(name="Group 2"),
            Group.objects.create(name="Group 3"),
        )

        users = (
            User.objects.create(
                username="User1",
                first_name="Hank",
                last_name="Hill",
                email="hank@stricklandpropane.com",
                is_staff=True,

            ),
            User.objects.create(
                username="User2",
                first_name="Dale",
                last_name="Gribble",
                email="dale@dalesdeadbug.com",
                # changes=changes.objects.get(id=1)
                # book.author.set(Author.objects.get(id=2))
            ),
            User.objects.create(
                username="User3",
                first_name="Bill",
                last_name="Dauterive",
                email="bill.dauterive@army.mil",
            ),
            User.objects.create(
                username="User4",
                first_name="Jeff",
                last_name="Boomhauer",
                email="boomhauer@dangolemail.com",
                config_data={'a': 'v', },
                logentry="zky",
            ),
            User.objects.create(
                username="User5",
                first_name="Debbie",
                last_name="Grund",
                is_active=False,
                config_data={'aa': 'ff', },
                logentry="xyz",

            ),
        )
        tenants = Tenant.objects.filter(group__isnull=False)
        cls.tenants = tenants

        regions = (
            Region.objects.create(name="Region 1", slug="region-1", description="A"),
            Region.objects.create(name="Region 2", slug="region-2", description="B"),
            Region.objects.create(name="Region 3", slug="region-3", description="C"),
        )
        cls.regions = regions

        site_statuses = Status.objects.get_for_model(Site)
        cls.site_status_map = {s.slug: s for s in site_statuses.all()}

        sites = (
            Site.objects.create(
                name="Site 1",
                slug="site-1",
                description="Site 1 description",
                region=regions[0],
                tenant=tenants[0],
                status=cls.site_status_map["active"],
                facility="Facility 1",
                asn=65001,
                latitude=10,
                longitude=10,
                contact_name="Contact 1",
                contact_phone="123-555-0001",
                contact_email="contact1@example.com",
                physical_address="1 road st, albany, ny",
                shipping_address="PO Box 1, albany, ny",
                comments="comment1",
                time_zone="America/Chicago",
            ),
            Site.objects.create(
                name="Site 2",
                slug="site-2",
                description="Site 2 description",
                region=regions[1],
                tenant=tenants[1],
                status=cls.site_status_map["planned"],
                facility="Facility 2",
                asn=65002,
                latitude=20,
                longitude=20,
                contact_name="Contact 2",
                contact_phone="123-555-0002",
                contact_email="contact2@example.com",
                physical_address="2 road st, albany, ny",
                shipping_address="PO Box 2, albany, ny",
                comments="comment2",
                time_zone="America/Los_Angeles",
            ),
            Site.objects.create(
                name="Site 3",
                slug="site-3",
                region=regions[2],
                tenant=tenants[2],
                status=cls.site_status_map["retired"],
                facility="Facility 3",
                asn=65003,
                latitude=30,
                longitude=30,
                contact_name="Contact 3",
                contact_phone="123-555-0003",
                contact_email="contact3@example.com",
                comments="comment3",
                time_zone="America/Detroit",
            ),
        )

        provider = Provider.objects.create(name="Provider 1", slug="provider-1", asn=65001, account="1234")
        circuit_type = CircuitType.objects.create(name="Test Circuit Type 1", slug="test-circuit-type-1")
        circuit = Circuit.objects.create(provider=provider, type=circuit_type, cid="Test Circuit 1")
        CircuitTermination.objects.create(circuit=circuit, site=sites[0], term_side="A")
        CircuitTermination.objects.create(circuit=circuit, site=sites[1], term_side="Z")

        manufacturers = list(Manufacturer.objects.all()[:3])
        cls.manufacturers = manufacturers

        rack_groups = (
            RackGroup.objects.create(name="Rack Group 1", slug="rack-group-1", site=sites[0]),
            RackGroup.objects.create(name="Rack Group 2", slug="rack-group-2", site=sites[1]),
            RackGroup.objects.create(name="Rack Group 3", slug="rack-group-3", site=sites[2]),
        )
        rackroles = (
            RackRole.objects.create(name="Rack Role 1", slug="rack-role-1", color="ff0000"),
            RackRole.objects.create(name="Rack Role 2", slug="rack-role-2", color="00ff00"),
            RackRole.objects.create(name="Rack Role 3", slug="rack-role-3", color="0000ff"),
        )

        rack_statuses = Status.objects.get_for_model(Rack)
        cls.rack_status_map = {s.slug: s for s in rack_statuses.all()}

        racks = (
            Rack.objects.create(
                name="Rack 1",
                comments="comment1",
                facility_id="rack-1",
                site=sites[0],
                group=rack_groups[0],
                tenant=tenants[0],
                status=cls.rack_status_map["active"],
                role=rackroles[0],
                serial="ABC",
                asset_tag="1001",
                type=RackTypeChoices.TYPE_2POST,
                width=RackWidthChoices.WIDTH_19IN,
                u_height=42,
                desc_units=False,
                outer_width=100,
                outer_depth=100,
                outer_unit=RackDimensionUnitChoices.UNIT_MILLIMETER,
            ),
            Rack.objects.create(
                name="Rack 2",
                comments="comment2",
                facility_id="rack-2",
                site=sites[1],
                group=rack_groups[1],
                tenant=tenants[1],
                status=cls.rack_status_map["planned"],
                role=rackroles[1],
                serial="DEF",
                asset_tag="1002",
                type=RackTypeChoices.TYPE_4POST,
                width=RackWidthChoices.WIDTH_21IN,
                u_height=43,
                desc_units=False,
                outer_width=200,
                outer_depth=200,
                outer_unit=RackDimensionUnitChoices.UNIT_MILLIMETER,
            ),
            Rack.objects.create(
                name="Rack 3",
                comments="comment3",
                facility_id="rack-3",
                site=sites[2],
                group=rack_groups[2],
                tenant=tenants[2],
                status=cls.rack_status_map["reserved"],
                role=rackroles[2],
                serial="GHI",
                asset_tag="1003",
                type=RackTypeChoices.TYPE_CABINET,
                width=RackWidthChoices.WIDTH_23IN,
                u_height=44,
                desc_units=True,
                outer_width=300,
                outer_depth=300,
                outer_unit=RackDimensionUnitChoices.UNIT_INCH,
            ),
        )
        rack_reservation = (
            RackReservation.objects.create(
                rack=racks[0],
                units=(1, 2, 3),
                user=users[0],
                description="Rack Reservation 1",
                tenant=tenants[0],
            ),
            RackReservation.objects.create(
                rack=racks[1],
                units=(4, 5, 6),
                user=users[1],
                description="Rack Reservation 2",
                tenant=tenants[1],
            ),
            RackReservation.objects.create(
                rack=racks[2],
                units=(7, 8, 9),
                user=users[2],
                description="Rack Reservation 3",
                tenant=tenants[2],
            ))
        # common_test_data(cls)
        future_date = make_aware(datetime.datetime(3000, 1, 1))
        past_date = make_aware(datetime.datetime(2000, 1, 1))
        tokens = (
            Token(user=users[0], key=Token.generate_key(), expires=future_date, write_enabled=True),
            Token(user=users[1], key=Token.generate_key(), expires=future_date, write_enabled=True),
            Token(user=users[2], key=Token.generate_key(), expires=past_date, write_enabled=False),
        )
        Token.objects.bulk_create(tokens)

        users[0].groups.set([groups[0]])
        users[1].groups.set([groups[1]])
        users[2].groups.set([groups[2]])

    def test_username(self):
        params = {"username": ["User1", "User2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_first_name(self):
        params = {"first_name": ["Hank", "Dale"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_last_name(self):
        params = {"last_name": ["Hill", "Gribble"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_email(self):
        params = {"email": ["hank@stricklandpropane.com", "dale@dalesdeadbug.com"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_is_staff(self):
        params = {"is_staff": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_is_active(self):
        params = {"is_active": True}
        # 4 created active users in setUpTestData, plus one created active user in TestCase.setUp
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 5)

    def test_group(self):
        groups = Group.objects.all()[:2]
        params = {"group_id": [groups[0].pk, groups[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"group": [groups[0].name, groups[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)

    def test_rack_reservation(self):
        rack_reservation = RackReservation.objects.all()[:2]
        print("got here!")
        params = {"rackreservation": [rack_reservation[0].pk, rack_reservation[1].pk]}
        print(self.filterset(params, self.queryset).qs.count())
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 6)

    def test_changes(self):
        params = {"changes": True}
        # 4 created active users in setUpTestData, plus one created active user in TestCase.setUp
        print(self.queryset)
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 20)

    # def test_tokens(self):
    #     params = {'tokens': [groups[0].pk, groups[1].pk]}

    # book = Book.objects.get(id=1)
    # book.author.set(Author.objects.get(id=2))


class GroupTestCase(FilterTestCases.FilterTestCase):
    queryset = Group.objects.all()
    filterset = GroupFilterSet

    @classmethod
    def setUpTestData(cls):
        Group.objects.create(name="Group 1")
        Group.objects.create(name="Group 2")
        Group.objects.create(name="Group 3")

    def test_name(self):
        params = {"name": ["Group 1", "Group 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class ObjectPermissionTestCase(FilterTestCases.FilterTestCase):
    queryset = ObjectPermission.objects.all()
    filterset = ObjectPermissionFilterSet

    @classmethod
    def setUpTestData(cls):
        groups = (
            Group.objects.create(name="Group 1"),
            Group.objects.create(name="Group 2"),
            Group.objects.create(name="Group 3"),
        )

        users = (
            User.objects.create(username="User1"),
            User.objects.create(username="User2"),
            User.objects.create(username="User3"),
        )

        object_types = (
            ContentType.objects.get(app_label="dcim", model="site"),
            ContentType.objects.get(app_label="dcim", model="rack"),
            ContentType.objects.get(app_label="dcim", model="device"),
        )

        permissions = (
            ObjectPermission.objects.create(name="Permission 1", actions=["view", "add", "change", "delete"]),
            ObjectPermission.objects.create(name="Permission 2", actions=["view", "add", "change", "delete"]),
            ObjectPermission.objects.create(name="Permission 3", actions=["view", "add", "change", "delete"]),
            ObjectPermission.objects.create(name="Permission 4", actions=["view"], enabled=False),
            ObjectPermission.objects.create(name="Permission 5", actions=["add"], enabled=False),
            ObjectPermission.objects.create(name="Permission 6", actions=["change"], enabled=False),
            ObjectPermission.objects.create(name="Permission 7", actions=["delete"], enabled=False),
        )
        for i in range(0, 3):
            permissions[i].groups.set([groups[i]])
            permissions[i].users.set([users[i]])
            permissions[i].object_types.set([object_types[i]])

    def test_name(self):
        params = {"name": ["Permission 1", "Permission 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_enabled(self):
        params = {"enabled": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_group(self):
        groups = Group.objects.filter(name__in=["Group 1", "Group 2"])
        params = {"group_id": [groups[0].pk, groups[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"group": [groups[0].name, groups[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_user(self):
        users = User.objects.filter(username__in=["User1", "User2"])
        params = {"user_id": [users[0].pk, users[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"user": [users[0].username, users[1].username]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_object_types(self):
        object_types = ContentType.objects.filter(model__in=["site", "rack"])
        params = {"object_types": [object_types[0].pk, object_types[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class TokenTestCase(FilterTestCases.FilterTestCase):
    queryset = Token.objects.all()
    filterset = TokenFilterSet

    @classmethod
    def setUpTestData(cls):
        users = (
            User(username="User1"),
            User(username="User2"),
            User(username="User3"),
        )
        User.objects.bulk_create(users)

        future_date = make_aware(datetime.datetime(3000, 1, 1))
        past_date = make_aware(datetime.datetime(2000, 1, 1))
        tokens = (
            Token(user=users[0], key=Token.generate_key(), expires=future_date, write_enabled=True),
            Token(user=users[1], key=Token.generate_key(), expires=future_date, write_enabled=True),
            Token(user=users[2], key=Token.generate_key(), expires=past_date, write_enabled=False),
        )
        Token.objects.bulk_create(tokens)

    def test_expires(self):
        params = {"expires": ["3000-01-01 00:00:00"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"expires__gte": ["2021-01-01 00:00:00"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"expires__lte": ["2021-01-01 00:00:00"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_key(self):
        tokens = Token.objects.all()[:2]
        params = {"key": [tokens[0].key, tokens[1].key]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_write_enabled(self):
        params = {"write_enabled": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"write_enabled": False}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)
