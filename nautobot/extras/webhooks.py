import logging
import socket
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils import timezone
import netaddr

from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.extras.models import Webhook
from nautobot.extras.registry import registry
from nautobot.extras.tasks import process_webhook

logger = logging.getLogger(__name__)


def _webhook_addr_is_builtin_blocked(addr):
    """Return True if ``addr`` is in a never-legitimate range. Admins cannot disable these via configuration."""
    # is_reserved covers IPv4 0.0.0.0, 240.0.0.0/4 (incl. 255.255.255.255 broadcast), IPv6 :: and the IETF-reserved
    # blocks (which include the IPv4-mapped IPv6 ::ffff:0:0/96 range, so an attacker can't bypass via that form).
    return addr.is_loopback() or addr.is_link_local() or addr.is_multicast() or addr.is_reserved()


def _webhook_additional_blocked_networks():
    return [netaddr.IPNetwork(cidr) for cidr in settings.WEBHOOK_ADDITIONAL_BLOCKED_NETWORKS]


def _webhook_host_matches_allow_list(host, allow_list):
    """Django ``ALLOWED_HOSTS``-style matching: literal hostname, ``.example.com`` subdomain wildcard, or ``*``."""
    if not host:
        return False
    host = host.lower().rstrip(".")
    for pattern in allow_list or []:
        pattern = pattern.lower().rstrip(".")
        if pattern == "*":
            return True
        if pattern.startswith("."):
            if host == pattern[1:] or host.endswith(pattern):
                return True
        elif host == pattern:
            return True
    return False


def _webhook_address_from_host(host):
    """
    Return a `netaddr.IPAddress` if `host` is an IP literal, else `None`.

    Does not perform DNS resolution -- DNS lookups are deferred to the Celery worker, since the web server and
    the worker may resolve names differently (split-horizon DNS, container DNS, K8s namespaces, etc.).
    """
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    try:
        return netaddr.IPAddress(host)
    except (netaddr.AddrFormatError, ValueError):
        return None


def _webhook_check_address_against_block_lists(host, addr, *, check_additional=True):
    """
    Raise `ValidationError` if `addr` falls in the built-in block-list, or (when `check_additional` is True)
    in the admin-extended block-list. The built-in block-list is enforced unconditionally and is NOT bypassed
    by `WEBHOOK_ALLOWED_HOSTS` -- callers pass `check_additional=False` for allow-listed hosts to skip only the
    admin-extended list.
    """
    if _webhook_addr_is_builtin_blocked(addr):
        logger.warning(
            "Webhook URL validation: host %r resolved to %s, which is in a built-in blocked range.", host, addr
        )
        raise ValidationError(
            f"Webhook URL host {host!r} is not permitted (resolves to a reserved/loopback/link-local address)."
        )
    if not check_additional:
        return
    for network in _webhook_additional_blocked_networks():
        if addr.version != network.version:
            continue
        if addr in network:
            logger.warning(
                "Webhook URL validation: host %r resolved to %s, which is in additional blocked network %s.",
                host,
                addr,
                network,
            )
            raise ValidationError(
                f"Webhook URL host {host!r} is not permitted. "
                "Add the host to WEBHOOK_ALLOWED_HOSTS if this target is intentional."
            )


def _webhook_validate_scheme_and_extract_host(url):
    """Shared scheme + URL syntax check. Returns the URL host."""
    if not url:
        raise ValidationError("Webhook URL is required.")

    allowed_schemes = list(settings.WEBHOOK_ALLOWED_SCHEMES)
    try:
        URLValidator(schemes=allowed_schemes)(url)
    except ValidationError as exc:
        scheme = urlsplit(url).scheme.lower()
        if scheme and scheme not in (s.lower() for s in allowed_schemes):
            raise ValidationError(
                f"Webhook URL scheme {scheme!r} is not permitted; allowed schemes are: {', '.join(allowed_schemes)}."
            )
        raise exc

    host = urlsplit(url).hostname
    if not host:
        raise ValidationError("Webhook URL must include a host.")
    return host


def validate_webhook_url_format(url):
    """
    Save-time validation: scheme, URL syntax, and built-in block-list check for IP-literal hosts.

    DNS resolution is intentionally NOT performed here because the web server and the Celery worker may have
    different DNS views; reliable name-based block-list enforcement happens at request-send time via
    `validate_webhook_url`.

    `WEBHOOK_ALLOWED_HOSTS` bypasses only the admin-extended block-list (`WEBHOOK_ADDITIONAL_BLOCKED_NETWORKS`).
    The built-in block-list (loopback, link-local, multicast, unspecified, reserved) is enforced unconditionally.

    Raises `django.core.exceptions.ValidationError` on any policy violation.
    """
    host = _webhook_validate_scheme_and_extract_host(url)
    allow_listed = _webhook_host_matches_allow_list(host, settings.WEBHOOK_ALLOWED_HOSTS)

    addr = _webhook_address_from_host(host)
    if addr is not None:
        _webhook_check_address_against_block_lists(host, addr, check_additional=not allow_listed)


def validate_webhook_url(url):
    """
    Send-time validation: everything `validate_webhook_url_format` does, plus DNS resolution and block-list
    check on every resolved address.

    Returns the validated IP that the caller should connect to (as a string). For IP-literal URLs the returned
    IP is the literal. The caller can use this to pin the outbound connection to the validated IP for
    DNS-rebinding mitigation.

    `WEBHOOK_ALLOWED_HOSTS` bypasses only the admin-extended block-list (`WEBHOOK_ADDITIONAL_BLOCKED_NETWORKS`).
    The built-in block-list (loopback, link-local, multicast, unspecified, reserved) is enforced unconditionally,
    so an allow-listed hostname whose DNS resolves to (e.g.) `169.254.169.254` is still rejected.

    Intended to be called from the Celery worker just before issuing the request, so the DNS view used here
    matches the one the request will actually use.

    Raises `django.core.exceptions.ValidationError` on any policy violation.
    """
    host = _webhook_validate_scheme_and_extract_host(url)
    allow_listed = _webhook_host_matches_allow_list(host, settings.WEBHOOK_ALLOWED_HOSTS)

    addr = _webhook_address_from_host(host)
    if addr is not None:
        _webhook_check_address_against_block_lists(host, addr, check_additional=not allow_listed)
        return str(addr)

    bare_host = host[1:-1] if host.startswith("[") and host.endswith("]") else host
    try:
        infos = socket.getaddrinfo(bare_host, None)
    except socket.gaierror as exc:
        logger.warning("Webhook URL validation: DNS resolution failed for host %r: %s", host, exc)
        raise ValidationError(f"Unable to resolve webhook host {host!r}.")

    chosen = None
    for info in infos:
        addr = netaddr.IPAddress(info[4][0])
        _webhook_check_address_against_block_lists(host, addr, check_additional=not allow_listed)
        if chosen is None:
            chosen = str(addr)
    return chosen


def enqueue_webhooks(object_change, snapshots=None, webhook_queryset=None):
    """
    Find Webhook(s) assigned to this instance + action and enqueue them to be processed.

    Args:
        object_change (ObjectChange): The change that may trigger Webhooks to be sent.
        snapshots (list): The before/after data snapshots corresponding to the object_change.
        webhook_queryset (QuerySet): Previously retrieved set of Webhooks to potentially send.

    Returns:
        webhook_queryset (QuerySet): for reuse when processing multiple ObjectChange with the same content-type+action.
    """
    # Determine whether this type of object supports webhooks
    app_label = object_change.changed_object_type.app_label
    model_name = object_change.changed_object_type.model
    if model_name not in registry["model_features"]["webhooks"].get(app_label, []):
        return webhook_queryset

    # Retrieve any applicable Webhooks
    content_type = object_change.changed_object_type
    action_flag = {
        ObjectChangeActionChoices.ACTION_CREATE: "type_create",
        ObjectChangeActionChoices.ACTION_UPDATE: "type_update",
        ObjectChangeActionChoices.ACTION_DELETE: "type_delete",
    }[object_change.action]
    if webhook_queryset is None:
        webhook_queryset = Webhook.objects.filter(content_types=content_type, enabled=True, **{action_flag: True})

    if webhook_queryset:  # not .exists() as we *want* to populate the queryset cache
        if snapshots is None:
            snapshots = object_change.get_snapshots()
        # fall back to object_data if object_data_v2 is not available
        serialized_data = object_change.object_data_v2
        if serialized_data is None:
            serialized_data = object_change.object_data

        # Enqueue the webhooks
        for webhook in webhook_queryset:
            args = [
                webhook.pk,
                serialized_data,
                model_name,
                object_change.action,
                str(timezone.now()),
                object_change.user_name,
                object_change.request_id,
                snapshots,
            ]
            process_webhook.apply_async(args=args)

    return webhook_queryset
