from django.core.exceptions import PermissionDenied
from django.db import models

from nautobot.core.choices import ChoiceSet
from nautobot.extras.jobs import DryRunVar, IPNetworkVar, Job, MultiChoiceVar, ObjectVar
from nautobot.ipam.models import get_default_namespace_pk, IPAddress, Namespace, Prefix

name = "System Jobs"


class CleanupTypes(ChoiceSet):
    IPADDRESS = "ipam.IPAddress"
    PREFIX = "ipam.Prefix"

    CHOICES = (
        (IPADDRESS, "IP addresses"),
        (PREFIX, "Prefixes"),
    )


class FixIPAMParents(Job):
    cleanup_types = MultiChoiceVar(
        choices=CleanupTypes.CHOICES, required=True, default=[CleanupTypes.IPADDRESS, CleanupTypes.PREFIX]
    )

    restrict_to_namespace = ObjectVar(
        model=Namespace, required=False, description="Check only records within this namespace"
    )
    restrict_to_network = IPNetworkVar(required=False, description="Check only records within this network")

    dryrun = DryRunVar()

    class Meta:
        name = "Check/Fix IPAM Parents"
        description = "Check for and/or fix incorrect 'parent' values on IP Address and/or Prefix records."
        has_sensitive_variables = False

    def run(  # pylint: disable=arguments-differ
        self, *, cleanup_types, restrict_to_namespace=None, restrict_to_network=None, dryrun=False
    ):
        all_relevant_prefixes = Prefix.objects.restrict(self.user, "change")

        if restrict_to_namespace is not None:
            self.logger.info(
                "Inspecting only records in namespace %s",
                restrict_to_namespace.name,
                extra={"object": restrict_to_namespace},
            )
            all_relevant_prefixes = all_relevant_prefixes.filter(namespace=restrict_to_namespace)
        if restrict_to_network is not None:
            self.logger.info("Inspecting only records that fall within %s", restrict_to_network)
            all_relevant_prefixes = all_relevant_prefixes.net_contained_or_equal(restrict_to_network)

        if CleanupTypes.PREFIX in cleanup_types:
            if not self.user.has_perm("ipam.change_prefix"):
                self.fail('User "%s" does not have permission to update Prefix records', self.user.username)
                raise PermissionDenied("User does not have update permission for Prefix records")

            self.logger.info("Inspecting Prefix records...")

            self.logger.debug("Beginning with a quick check for obviously wrong `parent` values...")
            # 1. Obviously wrong Prefix parents
            #    - parent is set but has wrong IP version
            #    - parent is set but has wrong namespace
            #    - parent is set but its network/broadcast range doesn't contain the given subnet
            prefixes_with_invalid_parents = (
                all_relevant_prefixes.exclude(parent__ip_version=models.F("ip_version"))
                | all_relevant_prefixes.exclude(parent__namespace_id=models.F("namespace_id"))
                | all_relevant_prefixes.filter(parent__network__gt=models.F("network"))
                | all_relevant_prefixes.filter(parent__broadcast__lt=models.F("broadcast"))
                | all_relevant_prefixes.filter(parent__prefix_length__gte=models.F("prefix_length"))
            ).exclude(parent__isnull=True)

            prefixes_with_invalid_parents = prefixes_with_invalid_parents.select_related("parent")

            if prefixes_with_invalid_parents.exists():
                fixed_prefixes = []
                for pfx in prefixes_with_invalid_parents:
                    candidate_parents = Prefix.objects.all()
                    # Preserve namespace
                    candidate_parents = candidate_parents.filter(namespace_id=pfx.namespace_id)
                    try:
                        parent = candidate_parents.get_closest_parent(pfx.prefix, include_self=False)
                    except Prefix.DoesNotExist:
                        parent = None
                    self.logger.warning(
                        "Parent for %s should be corrected from %s to %s",
                        pfx.prefix,
                        pfx.parent.display if pfx.parent is not None else None,
                        parent.display if parent is not None else None,
                        extra={"object": pfx},
                    )
                    pfx.parent = parent
                    fixed_prefixes.append(pfx)

                if dryrun:
                    self.logger.warning(
                        "Would correct invalid `parent` for %d Prefixes if this were not a dry-run", len(fixed_prefixes)
                    )
                else:
                    update_count = Prefix.objects.bulk_update(fixed_prefixes, ["parent"], batch_size=1000)
                    self.logger.success("Corrected invalid `parent` for %d Prefixes", update_count)
            else:
                self.logger.success("No Prefix records had clearly invalid `parent` values")

            self.logger.debug("Continuing by checking Prefixes with null `parent` to make sure that's correct...")
            # 2. parent is null but should not be
            fixed_prefixes = []
            processed_pfx_count = 0
            for pfx in all_relevant_prefixes.filter(parent__isnull=True):
                candidate_parents = Prefix.objects.all()
                # Preserve namespace
                candidate_parents = candidate_parents.filter(namespace_id=pfx.namespace_id)
                try:
                    parent = candidate_parents.get_closest_parent(pfx.prefix, include_self=False)
                except Prefix.DoesNotExist:
                    parent = None

                if parent is not None:
                    self.logger.warning(
                        "Parent for %s should be set to %s instead of None",
                        pfx.display,
                        parent.prefix,
                        extra={"object": pfx},
                    )
                    pfx.parent = parent
                    fixed_prefixes.append(pfx)
                processed_pfx_count += 1

            self.logger.debug(
                "Inspected %d Prefixes with null `parent` to see if an appropriate parent exists",
                processed_pfx_count,
            )

            if fixed_prefixes:
                if dryrun:
                    self.logger.warning(
                        "Would set a more precise `parent` for %d Prefixes if this were not a dry-run",
                        len(fixed_prefixes),
                    )
                else:
                    update_count = Prefix.objects.bulk_update(fixed_prefixes, ["parent"], batch_size=1000)
                    self.logger.success("Corrected imprecise `parent` for %d Prefixes", update_count)

            self.logger.debug("Continuing with a more involved check for more subtly incorrect `parent` values...")
            # 3. More subtly wrong Prefix parents
            #    - parent is set but a more specific parent Prefix also exists
            fixed_prefixes = []
            processed_pfx_count = 0
            for pfx in all_relevant_prefixes.filter(
                parent__prefix_length__lt=models.F("prefix_length") - 1
            ).select_related("parent"):
                try:
                    parent = pfx.parent.subnets(include_self=True).get_closest_parent(pfx.prefix, include_self=False)
                except Prefix.DoesNotExist:
                    parent = None
                if parent != pfx.parent:
                    self.logger.warning(
                        "Parent for %s should be corrected from %s to %s",
                        pfx.display,
                        pfx.parent.prefix if pfx.parent else None,
                        parent.prefix if parent else None,
                        extra={"object": pfx},
                    )
                    pfx.parent = parent
                    fixed_prefixes.append(pfx)
                processed_pfx_count += 1

            self.logger.debug(
                "Inspected %d Prefixes for more subtly incorrect `parent` values",
                processed_pfx_count,
            )

            if fixed_prefixes:
                if dryrun:
                    self.logger.warning(
                        "Would set a more precise `parent` for %d Prefixes if this were not a dry-run",
                        len(fixed_prefixes),
                    )
                else:
                    update_count = Prefix.objects.bulk_update(fixed_prefixes, ["parent"], batch_size=1000)
                    self.logger.success("Corrected imprecise `parent` for %d Prefixes", update_count)

        if CleanupTypes.IPADDRESS in cleanup_types:
            if not self.user.has_perm("ipam.change_ipaddress"):
                self.fail('User "%s" does not have permission to update IP Address records', self.user.username)
                raise PermissionDenied("User does not have update permission for IP Address records")

            self.logger.info("Inspecting IP Address records...")

            all_relevant_ips = IPAddress.objects.restrict(self.user, "change")
            if restrict_to_namespace is not None:
                self.logger.info("Inspecting only records in namespace %s", restrict_to_namespace.name)
                all_relevant_ips = all_relevant_ips.filter(parent__namespace=restrict_to_namespace)
            if restrict_to_network is not None:
                self.logger.info("Inspecting only records that fall within %s", restrict_to_network)
                all_relevant_ips = all_relevant_ips.net_host_contained(restrict_to_network)

            self.logger.debug("Beginning with a quick check for obviously wrong `parent` values...")
            # 4. Obviously wrong IPAddress parents
            #    - parent is unset entirely
            #    - parent is set but has wrong IP version
            #    - parent is set but its network/broadcast range doesn't contain the given host IP
            ips_with_invalid_parents = (
                all_relevant_ips.filter(parent__isnull=True)
                | all_relevant_ips.exclude(parent__ip_version=models.F("ip_version"))
                | all_relevant_ips.filter(parent__network__gt=models.F("host"))
                | all_relevant_ips.filter(parent__broadcast__lt=models.F("host"))
            )

            ips_with_invalid_parents = ips_with_invalid_parents.select_related("parent")

            if ips_with_invalid_parents.exists():
                fixed_ips = []
                for ip in ips_with_invalid_parents:
                    candidate_parents = Prefix.objects.all()
                    # Preserve namespace
                    if ip.parent is not None:
                        candidate_parents = candidate_parents.filter(namespace_id=ip.parent.namespace_id)
                    else:
                        candidate_parents = candidate_parents.filter(namespace_id=get_default_namespace_pk())
                    try:
                        parent = candidate_parents.get_closest_parent(ip.host, include_self=True)
                        self.logger.warning(
                            "Parent for %s should be corrected from %s to %s",
                            ip.host,
                            ip.parent.prefix if ip.parent is not None else None,
                            parent.prefix,
                            extra={"object": ip},
                        )
                        ip.parent = parent
                        fixed_ips.append(ip)
                    except Prefix.DoesNotExist:
                        self.logger.warning(
                            "No valid parent Prefix could be identified for %s. "
                            "You should create a %s/%d Prefix or similar to contain this IP Address.",
                            ip.host,
                            ip.address.network,
                            ip.mask_length,
                            extra={"object": ip},
                        )

                if dryrun:
                    self.logger.warning(
                        "Would correct invalid `parent` for %d IP Addresses if this were not a dry-run", len(fixed_ips)
                    )
                else:
                    update_count = IPAddress.objects.bulk_update(fixed_ips, ["parent"], batch_size=1000)
                    self.logger.success("Corrected invalid `parent` for %d IP Addresses", update_count)
            else:
                self.logger.success("No IP Address records had null or clearly invalid `parent` values")

            self.logger.debug("Continuing with a more involved check for more subtly incorrect `parent` values...")
            # 5. More subtly wrong IPAddress parents
            #    - parent is set and contains the IP, but is not the most specific such Prefix
            fixed_ips = []
            processed_ip_count = 0
            for ip in all_relevant_ips.exclude(parent__children__isnull=True).select_related("parent"):
                candidate_parents = ip.parent.subnets(include_self=True)
                try:
                    parent = candidate_parents.get_closest_parent(ip.host, include_self=True)
                    if parent.id != ip.parent_id:
                        self.logger.warning(
                            "Parent for %s should be corrected from %s to %s",
                            ip.host,
                            ip.parent.prefix,
                            parent.prefix,
                            extra={"object": ip},
                        )
                        ip.parent = parent
                        fixed_ips.append(ip)
                except Prefix.DoesNotExist:
                    self.logger.warning(
                        "No valid parent Prefix could be identified for %s. "
                        "You should create a %s/%d Prefix or similar to contain this IP Address.",
                        ip.host,
                        ip.address.network,
                        ip.mask_length,
                        extra={"object": ip},
                    )
                processed_ip_count += 1

            self.logger.debug(
                "Inspected %d IP Addresses for more subtly incorrect `parent` values",
                processed_ip_count,
            )

            if fixed_ips:
                if dryrun:
                    self.logger.warning(
                        "Would set a more precise `parent` for %d IP Addresses if this were not a dry-run",
                        len(fixed_ips),
                    )
                else:
                    update_count = IPAddress.objects.bulk_update(fixed_ips, ["parent"], batch_size=1000)
                    self.logger.success("Corrected imprecise `parent` for %d IP Addresses", update_count)
