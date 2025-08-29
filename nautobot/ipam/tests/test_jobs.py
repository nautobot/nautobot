from django.contrib.contenttypes.models import ContentType
import netaddr

from nautobot.core.testing import create_job_result_and_run_job, TransactionTestCase
from nautobot.extras.choices import JobResultStatusChoices, LogLevelChoices
from nautobot.extras.models import JobLogEntry, Status
from nautobot.ipam.models import get_default_namespace, IPAddress, Namespace, Prefix
from nautobot.users.models import ObjectPermission


class FixIPAMParentsTestCase(TransactionTestCase):
    """Tests for the FixIPAMParents system Job."""

    databases = ("default", "job_logs")

    def setUp(self):
        super().setUp()

        self.status, _ = Status.objects.get_or_create(name="Active")
        self.status.content_types.add(ContentType.objects.get_for_model(IPAddress))
        self.status.content_types.add(ContentType.objects.get_for_model(Prefix))

        # Create the "intended" hierarchy of records to test
        self.root = Prefix.objects.create(prefix="10.0.0.0/8", status=self.status)
        self.branch1 = Prefix.objects.create(prefix="10.1.0.0/16", status=self.status)
        self.leaf11 = Prefix.objects.create(prefix="10.1.1.0/24", status=self.status)
        self.leaf12 = Prefix.objects.create(prefix="10.1.2.0/24", status=self.status)
        self.leaf13 = Prefix.objects.create(prefix="10.1.3.0/24", status=self.status)
        self.leaf14 = Prefix.objects.create(prefix="10.1.4.0/24", status=self.status)
        self.branch2 = Prefix.objects.create(prefix="10.2.0.0/16", status=self.status)
        self.leaf21 = Prefix.objects.create(prefix="10.2.1.0/24", status=self.status)

        self.ip111 = IPAddress.objects.create(address="10.1.1.1/24", status=self.status)
        self.ip112 = IPAddress.objects.create(address="10.1.1.2/24", status=self.status)
        self.ip121 = IPAddress.objects.create(address="10.1.2.1/24", status=self.status)
        self.ip122 = IPAddress.objects.create(address="10.1.2.2/24", status=self.status)
        self.ip201 = IPAddress.objects.create(address="10.2.0.1/16", status=self.status)
        self.ip211 = IPAddress.objects.create(address="10.2.1.1/24", status=self.status)
        self.ip212 = IPAddress.objects.create(address="10.2.1.2/24", status=self.status)
        self.ip213 = IPAddress.objects.create(address="10.2.1.3/24", status=self.status)
        self.ip214 = IPAddress.objects.create(address="10.2.1.4/24", status=self.status)

        self.other_namespace = Namespace.objects.create(name="Some other namespace")
        self.other_branch3 = Prefix.objects.create(
            prefix="10.3.0.0/16", status=self.status, namespace=self.other_namespace
        )
        self.other_leaf31 = Prefix.objects.create(
            prefix="10.3.1.0/24", status=self.status, namespace=self.other_namespace
        )
        self.other_ip = IPAddress.objects.create(address="10.3.1.1/24", status=self.status, parent=self.other_leaf31)

        self.all_pfxs = {
            self.root,
            self.branch1,
            self.leaf11,
            self.leaf12,
            self.leaf13,
            self.leaf14,
            self.branch2,
            self.leaf21,
            self.other_branch3,
            self.other_leaf31,
        }
        self.all_ips = {
            self.ip111,
            self.ip112,
            self.ip121,
            self.ip122,
            self.ip201,
            self.ip211,
            self.ip212,
            self.ip213,
            self.ip214,
            self.other_ip,
        }

    def assert_ip_parents(self, expected_parentage: dict):
        self.assertEqual(set(expected_parentage.keys()), self.all_ips)
        for ip, expected_parent in expected_parentage.items():
            ip.refresh_from_db()
            self.assertEqual(
                ip.parent,
                expected_parent,
                f"parent of IP {ip.host} is expected to be {expected_parent.prefix if expected_parent else None} but "
                f"is instead {ip.parent.prefix if ip.parent else None}",
            )

    def assert_prefix_parents(self, expected_parentage: dict):
        self.assertEqual(set(expected_parentage.keys()), self.all_pfxs)
        for pfx, expected_parent in expected_parentage.items():
            pfx.refresh_from_db()
            self.assertEqual(
                pfx.parent,
                expected_parent,
                f"parent of prefix {pfx.prefix} should be {expected_parent.prefix if expected_parent else None} but "
                f"is {pfx.parent.prefix if pfx.parent else None}",
            )

    def test_initial_parentage_correct(self):
        self.assert_prefix_parents(
            {
                self.root: None,
                self.branch1: self.root,
                self.leaf11: self.branch1,
                self.leaf12: self.branch1,
                self.leaf13: self.branch1,
                self.leaf14: self.branch1,
                self.branch2: self.root,
                self.leaf21: self.branch2,
                self.other_branch3: None,
                self.other_leaf31: self.other_branch3,
            }
        )

        self.assert_ip_parents(
            {
                self.ip111: self.leaf11,
                self.ip112: self.leaf11,
                self.ip121: self.leaf12,
                self.ip122: self.leaf12,
                self.ip201: self.branch2,
                self.ip211: self.leaf21,
                self.ip212: self.leaf21,
                self.ip213: self.leaf21,
                self.ip214: self.leaf21,
                self.other_ip: self.other_leaf31,
            }
        )

    def corrupt_the_hierarchy(self):
        """
        Make 'bad' data for testing purposes.

        Uses QuerySet.update() because that bypasses clean/save validation.
        """
        # Change leaf11 to a different subnet, but don't update the parent of ip111 and ip112 accordingly
        Prefix.objects.filter(id=self.leaf11.id).update(network="10.2.0.0", broadcast="10.2.0.255")
        self.leaf11.refresh_from_db()
        # Change leaf13 to have an incorrect null parent
        Prefix.objects.filter(id=self.leaf13.id).update(parent=None)
        self.leaf13.refresh_from_db()
        # Change ip213 to have an incorrect/invalid null parent
        IPAddress.objects.filter(id=self.ip213.id).update(parent=None)
        self.ip213.refresh_from_db()
        # Change other_branch3 to have cross-namespace parentage
        Prefix.objects.filter(id=self.other_branch3.id).update(parent=self.root)
        self.other_branch3.refresh_from_db()
        # Change leaf14 to have a valid but not most-specific parent
        Prefix.objects.filter(id=self.leaf14.id).update(parent=self.root)
        self.leaf14.refresh_from_db()
        # Change ip214 and other_ip to have a valid but not most-specific parent
        IPAddress.objects.filter(id=self.ip214.id).update(parent=self.root)
        self.ip214.refresh_from_db()
        IPAddress.objects.filter(id=self.other_ip.id).update(parent=self.other_branch3)
        self.other_ip.refresh_from_db()

        self.corrupted_ip_parents = {
            self.ip111: self.leaf11,  # wrong
            self.ip112: self.leaf11,  # wrong
            self.ip121: self.leaf12,
            self.ip122: self.leaf12,
            self.ip201: self.branch2,  # wrong
            self.ip211: self.leaf21,
            self.ip212: self.leaf21,
            self.ip213: None,  # wrong
            self.ip214: self.root,  # wrong
            self.other_ip: self.other_branch3,  # wrong
        }

        self.corrupted_pfx_parents = {
            self.root: None,
            self.branch1: self.root,
            self.leaf11: self.branch1,  # wrong
            self.leaf12: self.branch1,
            self.leaf13: None,  # wrong
            self.leaf14: self.root,  # wrong
            self.branch2: self.root,
            self.leaf21: self.branch2,
            self.other_branch3: self.root,  # wrong
            self.other_leaf31: self.other_branch3,
        }

        self.repaired_ip_parents = {
            self.ip111: self.branch1,  # corrected after change of leaf11
            self.ip112: self.branch1,  # corrected after change of leaf11
            self.ip121: self.leaf12,
            self.ip122: self.leaf12,
            self.ip201: self.leaf11,  # corrected after change of leaf11
            self.ip211: self.leaf21,
            self.ip212: self.leaf21,
            self.ip213: self.leaf21,  # corrected from null
            self.ip214: self.leaf21,  # corrected from root
            self.other_ip: self.other_leaf31,  # corrected from other_branch3
        }

        self.repaired_pfx_parents = {
            self.root: None,
            self.branch1: self.root,
            self.leaf11: self.branch2,  # corrected after network change
            self.leaf12: self.branch1,
            self.leaf13: self.branch1,  # corrected from null
            self.leaf14: self.branch1,  # corrected from root
            self.branch2: self.root,
            self.leaf21: self.branch2,
            self.other_branch3: None,  # corrected from cross-namespace linkage
            self.other_leaf31: self.other_branch3,
        }

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

        self.assert_prefix_parents(self.repaired_pfx_parents)
        self.assert_ip_parents(self.repaired_ip_parents)

    def test_dryrun(self):
        self.corrupt_the_hierarchy()  # 🤘

        job_result = create_job_result_and_run_job(
            "nautobot.ipam.jobs.cleanup",
            "FixIPAMParents",
            cleanup_types=("ipam.IPAddress", "ipam.Prefix"),
            restrict_to_namespace=None,
            restrict_to_network=None,
            dryrun=True,
        )
        self.assertJobResultStatus(job_result)

        self.assert_prefix_parents(self.corrupted_pfx_parents)  # no change
        self.assert_ip_parents(self.corrupted_ip_parents)  # no change

    def test_fixup_without_permissions(self):
        self.corrupt_the_hierarchy()  # 🤘

        for cleanup_type, modelname in (
            ("ipam.IPAddress", "IP Address"),
            ("ipam.Prefix", "Prefix"),
        ):
            job_result = create_job_result_and_run_job(
                "nautobot.ipam.jobs.cleanup",
                "FixIPAMParents",
                username=self.user.username,  # otherwise this API defaults to using a superuser account
                cleanup_types=[cleanup_type],
                restrict_to_namespace=None,
                restrict_to_network=None,
                dryrun=False,
            )
            self.assertJobResultStatus(job_result, JobResultStatusChoices.STATUS_FAILURE)
            log_failure = JobLogEntry.objects.get(job_result=job_result, log_level=LogLevelChoices.LOG_FAILURE)
            self.assertEqual(
                log_failure.message,
                f'User "{self.user.username}" does not have permission to update {modelname} records',
            )

            self.assert_prefix_parents(self.corrupted_pfx_parents)  # no change
            self.assert_ip_parents(self.corrupted_ip_parents)  # no change

    def test_fixup_with_constrained_permissions(self):
        self.corrupt_the_hierarchy()  # 🤘

        prefix_perm = ObjectPermission.objects.create(
            name="Prefix permission",
            actions=["view", "change"],
            constraints={"network__net_contained_or_equal": str(self.branch2.prefix)},
        )
        prefix_perm.users.add(self.user)
        prefix_perm.object_types.add(ContentType.objects.get_for_model(Prefix))

        ip_perm = ObjectPermission.objects.create(
            name="IPAddress permission",
            actions=["view", "change"],
            constraints={"host__net_host_contained": str(self.branch2.prefix)},
        )
        ip_perm.users.add(self.user)
        ip_perm.object_types.add(ContentType.objects.get_for_model(IPAddress))

        job_result = create_job_result_and_run_job(
            "nautobot.ipam.jobs.cleanup",
            "FixIPAMParents",
            username=self.user.username,
            cleanup_types=("ipam.IPAddress", "ipam.Prefix"),
            restrict_to_namespace=None,
            restrict_to_network=None,
            dryrun=False,
        )
        self.assertJobResultStatus(job_result)

        self.assert_prefix_parents(
            {
                **{
                    pfx: parent
                    for pfx, parent in self.repaired_pfx_parents.items()
                    if pfx.prefix >= self.branch2.prefix
                    and netaddr.IPAddress(pfx.broadcast) <= netaddr.IPAddress(self.branch2.broadcast)
                },
                **{
                    pfx: parent
                    for pfx, parent in self.corrupted_pfx_parents.items()
                    if pfx.prefix < self.branch2.prefix
                    or netaddr.IPAddress(pfx.broadcast) > netaddr.IPAddress(self.branch2.broadcast)
                },
            }
        )

        self.assert_ip_parents(
            {
                **{
                    ip: parent
                    for ip, parent in self.repaired_ip_parents.items()
                    if ip.address >= self.branch2.prefix and ip.address <= netaddr.IPAddress(self.branch2.broadcast)
                },
                **{
                    ip: parent
                    for ip, parent in self.corrupted_ip_parents.items()
                    if ip.address < self.branch2.prefix or ip.address > netaddr.IPAddress(self.branch2.broadcast)
                },
            }
        )

    def test_cleanup_ips_only(self):
        self.corrupt_the_hierarchy()  # 🤘

        ip_perm = ObjectPermission.objects.create(
            name="IPAddress permission",
            actions=["view", "change"],
        )
        ip_perm.users.add(self.user)
        ip_perm.object_types.add(ContentType.objects.get_for_model(IPAddress))

        job_result = create_job_result_and_run_job(
            "nautobot.ipam.jobs.cleanup",
            "FixIPAMParents",
            username=self.user.username,
            cleanup_types=("ipam.IPAddress"),
            restrict_to_namespace=None,
            restrict_to_network=None,
            dryrun=False,
        )
        self.assertJobResultStatus(job_result)

        self.assert_ip_parents(self.repaired_ip_parents)  # repaired
        self.assert_prefix_parents(self.corrupted_pfx_parents)  # no change

    def test_cleanup_prefixes_only(self):
        self.corrupt_the_hierarchy()  # 🤘

        prefix_perm = ObjectPermission.objects.create(
            name="Prefix permission",
            actions=["view", "change"],
        )
        prefix_perm.users.add(self.user)
        prefix_perm.object_types.add(ContentType.objects.get_for_model(Prefix))

        job_result = create_job_result_and_run_job(
            "nautobot.ipam.jobs.cleanup",
            "FixIPAMParents",
            username=self.user.username,
            cleanup_types=("ipam.Prefix"),
            restrict_to_namespace=None,
            restrict_to_network=None,
            dryrun=False,
        )
        self.assertJobResultStatus(job_result)

        self.assert_ip_parents(self.corrupted_ip_parents)  # no change
        self.assert_prefix_parents(self.repaired_pfx_parents)  # repaired

    def test_cleanup_restrict_to_namespace(self):
        self.corrupt_the_hierarchy()  # 🤘

        default_ns = get_default_namespace()
        job_result = create_job_result_and_run_job(
            "nautobot.ipam.jobs.cleanup",
            "FixIPAMParents",
            cleanup_types=("ipam.IPAddress", "ipam.Prefix"),
            restrict_to_namespace=default_ns.pk,
            restrict_to_network=None,
            dryrun=False,
        )
        self.assertJobResultStatus(job_result)

        self.assert_prefix_parents(
            {
                **{pfx: parent for pfx, parent in self.repaired_pfx_parents.items() if pfx.namespace == default_ns},
                **{pfx: parent for pfx, parent in self.corrupted_pfx_parents.items() if pfx.namespace != default_ns},
            }
        )
        self.assert_ip_parents(
            {
                **{
                    ip: parent
                    for ip, parent in self.repaired_ip_parents.items()
                    if ip.parent and ip.parent.namespace == default_ns
                },
                **{
                    ip: parent
                    for ip, parent in self.corrupted_ip_parents.items()
                    if not ip.parent or ip.parent.namespace != default_ns
                },
            }
        )

    def test_cleanup_restrict_to_network(self):
        self.corrupt_the_hierarchy()  # 🤘

        job_result = create_job_result_and_run_job(
            "nautobot.ipam.jobs.cleanup",
            "FixIPAMParents",
            cleanup_types=("ipam.IPAddress", "ipam.Prefix"),
            restrict_to_namespace=None,
            restrict_to_network=str(self.branch1.prefix),
            dryrun=False,
        )
        self.assertJobResultStatus(job_result)

        self.assert_prefix_parents(
            {
                **{
                    pfx: parent
                    for pfx, parent in self.repaired_pfx_parents.items()
                    if pfx.prefix >= self.branch1.prefix
                    and netaddr.IPAddress(pfx.broadcast) <= netaddr.IPAddress(self.branch1.broadcast)
                },
                **{
                    pfx: parent
                    for pfx, parent in self.corrupted_pfx_parents.items()
                    if pfx.prefix < self.branch1.prefix
                    or netaddr.IPAddress(pfx.broadcast) > netaddr.IPAddress(self.branch1.broadcast)
                },
            }
        )
        self.assert_ip_parents(
            {
                **{
                    ip: parent
                    for ip, parent in self.repaired_ip_parents.items()
                    if ip.address >= self.branch1.prefix and ip.address <= netaddr.IPAddress(self.branch1.broadcast)
                },
                **{
                    ip: parent
                    for ip, parent in self.corrupted_ip_parents.items()
                    if ip.address < self.branch1.prefix or ip.address > netaddr.IPAddress(self.branch1.broadcast)
                },
            }
        )
