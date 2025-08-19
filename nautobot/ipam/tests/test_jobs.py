from django.contrib.contenttypes.models import ContentType

from nautobot.core.testing import create_job_result_and_run_job, TransactionTestCase
from nautobot.extras.models import Status
from nautobot.ipam.models import IPAddress, Namespace, Prefix
from nautobot.ipam.utils.testing import create_prefixes_and_ips


class FixIPAMParentsTestCase(TransactionTestCase):
    """Tests for the FixIPAMParents system Job."""

    databases = ("default", "job_logs")

    def setUp(self):
        self.status, _ = Status.objects.get_or_create(name="Active")
        self.status.content_types.add(ContentType.objects.get_for_model(IPAddress))
        self.status.content_types.add(ContentType.objects.get_for_model(Prefix))

        # Create the "intended" hierarchy of records to test
        self.root = Prefix.objects.create(prefix="10.0.0.0/8", status=self.status)
        self.branch1 = Prefix.objects.create(prefix="10.11.0.0/16", status=self.status)
        self.leaf11 = Prefix.objects.create(prefix="10.11.12.0/24", status=self.status)
        self.leaf12 = Prefix.objects.create(prefix="10.11.13.0/24", status=self.status)
        self.leaf13 = Prefix.objects.create(prefix="10.11.14.0/24", status=self.status)
        self.leaf14 = Prefix.objects.create(prefix="10.11.15.0/24", status=self.status)
        self.branch2 = Prefix.objects.create(prefix="10.12.0.0/16", status=self.status)
        self.leaf21 = Prefix.objects.create(prefix="10.12.14.0/24", status=self.status)

        self.ip111 = IPAddress.objects.create(address="10.11.12.1/24", status=self.status)
        self.ip112 = IPAddress.objects.create(address="10.11.12.2/24", status=self.status)
        self.ip121 = IPAddress.objects.create(address="10.11.13.1/24", status=self.status)
        self.ip122 = IPAddress.objects.create(address="10.11.13.2/24", status=self.status)
        self.ip21 = IPAddress.objects.create(address="10.12.13.1/16", status=self.status)
        self.ip211 = IPAddress.objects.create(address="10.12.14.1/24", status=self.status)
        self.ip212 = IPAddress.objects.create(address="10.12.14.2/24", status=self.status)
        self.ip213 = IPAddress.objects.create(address="10.12.14.3/24", status=self.status)
        self.ip214 = IPAddress.objects.create(address="10.12.14.4/24", status=self.status)

        self.other_namespace = Namespace.objects.create(name="Some other namespace")
        self.other_branch3 = Prefix.objects.create(
            prefix="10.13.0.0/16", status=self.status, namespace=self.other_namespace
        )

        # Add a few thousand "correct" records to confirm adequate performance of the Job
        create_prefixes_and_ips("10.0.0.0/16")

    def test_initial_parentage_correct(self):
        for obj, expected_parent in (
            (self.root, None),
            (self.branch1, self.root),
            (self.leaf11, self.branch1),
            (self.leaf12, self.branch1),
            (self.leaf13, self.branch1),
            (self.leaf14, self.branch1),
            (self.branch2, self.root),
            (self.leaf21, self.branch2),
            (self.other_branch3, None),
        ):
            obj.refresh_from_db()
            self.assertEqual(
                obj.parent,
                expected_parent,
                f"parent of {obj.network} should be {expected_parent.network if expected_parent else None} but "
                f"is {obj.parent.network if obj.parent else None}",
            )

        for obj, expected_parent in (
            (self.ip111, self.leaf11),
            (self.ip112, self.leaf11),
            (self.ip121, self.leaf12),
            (self.ip122, self.leaf12),
            (self.ip21, self.branch2),
            (self.ip211, self.leaf21),
            (self.ip212, self.leaf21),
            (self.ip213, self.leaf21),
            (self.ip214, self.leaf21),
        ):
            obj.refresh_from_db()
            self.assertEqual(
                obj.parent,
                expected_parent,
                f"parent of {obj.host} should be {expected_parent.network} but "
                f"is {obj.parent.network if obj.parent else None}",
            )

    def corrupt_the_hierarchy(self):
        """
        Make 'bad' data for testing purposes.

        Uses QuerySet.update() because that bypasses clean/save validation.
        """
        # Change leaf11 to a different subnet, but don't update its ip_addresses accordingly
        Prefix.objects.filter(id=self.leaf11.id).update(network="10.12.13.0", broadcast="10.12.13.255")
        # Change leaf13 to have an incorrect null parent
        Prefix.objects.filter(id=self.leaf13.id).update(parent=None)
        # Change ip213 to have an incorrect/invalid null parent
        IPAddress.objects.filter(id=self.ip213.id).update(parent=None)
        # Change other_branch3 to have cross-namespace parentage
        Prefix.objects.filter(id=self.other_branch3.id).update(parent=self.root)
        # Change leaf14 to have a valid but not most-specific parent
        Prefix.objects.filter(id=self.leaf14.id).update(parent=self.root)
        # Change ip214 to have a valid but not most-specific parent
        IPAddress.objects.filter(id=self.ip214.id).update(parent=self.root)

    # TODO: test with restricted or no permissions

    def test_fixup_all(self):
        self.corrupt_the_hierarchy()  # 🤘

        job_result = create_job_result_and_run_job(
            "nautobot.ipam.jobs.cleanup",
            "FixIPAMParents",
            cleanup_types=("ipam.IPAddress", "ipam.Prefix"),
            restrict_to_namespace=None,
            restrict_to_network=None,
            dryrun=False,
        )
        self.assertJobResultStatus(job_result)

        for obj, expected_parent in (
            (self.root, None),
            (self.branch1, self.root),
            (self.leaf11, self.branch2),  # corrected after network change
            (self.leaf12, self.branch1),
            (self.leaf13, self.branch1),  # corrected from null
            (self.leaf14, self.branch1),  # corrected from root
            (self.branch2, self.root),
            (self.leaf21, self.branch2),
            (self.other_branch3, None),  # corrected from cross-namespace linkage
        ):
            obj.refresh_from_db()
            self.assertEqual(
                obj.parent,
                expected_parent,
                f"parent of {obj.network} should be {expected_parent.network if expected_parent else None} but "
                f"is {obj.parent.network if obj.parent else None}",
            )

        for obj, expected_parent in (
            (self.ip111, self.branch1),  # corrected after change of leaf11
            (self.ip112, self.branch1),  # corrected after change of leaf11
            (self.ip121, self.leaf12),
            (self.ip122, self.leaf12),
            (self.ip21, self.leaf11),  # corrected after change of leaf11
            (self.ip211, self.leaf21),
            (self.ip212, self.leaf21),
            (self.ip213, self.leaf21),  # corrected from null
            (self.ip214, self.leaf21),  # corrected from root
        ):
            obj.refresh_from_db()
            self.assertEqual(
                obj.parent,
                expected_parent,
                f"parent of {obj.host} should be {expected_parent.network} but "
                f"is {obj.parent.network if obj.parent else None}",
            )

    # TODO: test with single cleanup_types value
    # TODO: test with restrict_to_namespace
    # TODO: test with restrict_to_network
    # TODO: test with restrict_to_namespace AND restrict_to_network
    # TODO: test with dryrun=True
