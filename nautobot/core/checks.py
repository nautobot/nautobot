from django.conf import settings
from django.core.checks import register, Error, Tags, Warning
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.encoding import force_bytes

from cryptography.hazmat.primitives.kdf import pbkdf2


E001 = Error(
    "CACHEOPS_DEFAULTS['timeout'] value cannot be 0. To disable caching set CACHEOPS_ENABLED=False.",
    id="nautobot.core.E001",
    obj=settings,
)

E002 = Error(
    "'nautobot.core.authentication.ObjectPermissionBackend' must be included in AUTHENTICATION_BACKENDS",
    id="nautobot.core.E002",
    obj=settings,
)

E003 = Error(
    "RELEASE_CHECK_TIMEOUT must be at least 3600 seconds (1 hour)",
    id="nautobot.core.E003",
    obj=settings,
)

E004 = Error(
    "RELEASE_CHECK_URL must be a valid API URL. Example: https://api.github.com/repos/nautobot/nautobot",
    id="nautobot.core.E004",
    obj=settings,
)

W005 = Warning(
    "STORAGE_CONFIG has been set but STORAGE_BACKEND is not defined. STORAGE_CONFIG will be ignored.",
    id="nautobot.core.W005",
    obj=settings,
)


class E006(Error):
    msg = "RQ_QUEUES must define at least the minimum set of required queues"
    id = "nautobot.core.E006"
    obj = settings


E007 = Error(
    "CRYPTOGRAPHY_KEY must be set to a non-null value that differs from SECRET_KEY."
    "\nIf you already have encrypted data in your database (such as Git repository access tokens), to avoid errors, "
    "you should make the following changes:"
    "\n1. Set CRYPTOGRAPHY_KEY to the current value of SECRET_KEY."
    "\n2. Generate a new SECRET_KEY value with 'nautobot-server generate_secret_key' and update your configuration.",
    id="nautobot.core.E007",
    obj=settings,
)


@register(Tags.caches)
def check_cache_timeout(app_configs, **kwargs):
    if settings.CACHEOPS_DEFAULTS.get("timeout") == 0:
        return [E001]
    return []


@register(Tags.security)
def check_object_permissions_backend(app_configs, **kwargs):
    if "nautobot.core.authentication.ObjectPermissionBackend" not in settings.AUTHENTICATION_BACKENDS:
        return [E002]
    return []


@register(Tags.compatibility)
def check_release_check_timeout(app_configs, **kwargs):
    if settings.RELEASE_CHECK_TIMEOUT < 3600:
        return [E003]
    return []


@register(Tags.compatibility)
def check_release_check_url(app_configs, **kwargs):
    validator = URLValidator()
    if settings.RELEASE_CHECK_URL:
        try:
            validator(settings.RELEASE_CHECK_URL)
        except ValidationError:
            return [E004]
    return []


@register(Tags.compatibility)
def check_storage_config_and_backend(app_configs, **kwargs):
    if settings.STORAGE_CONFIG and (settings.STORAGE_BACKEND is None):
        return [W005]
    return []


@register(Tags.compatibility)
def check_minimum_rq_queues(app_configs, **kwargs):
    errors = []
    minimum_queues = ["default", "webhooks", "check_releases", "custom_fields"]
    for queue in minimum_queues:
        if settings.RQ_QUEUES and not settings.RQ_QUEUES.get(queue):
            errors.append(
                E006(
                    E006.msg,
                    hint=f"RQ_QUEUES is missing the required '{queue}' queue definition",
                    obj=E006.obj,
                    id=E006.id,
                )
            )
    return errors


@register(Tags.security)
def check_cryptography_key_set(app_configs, **kwargs):
    # This is a bit ugly, because django-cryptography actually overwrites the CRYPTOGRAPHY_KEY setting
    # with a derived value at loading time. So even if it was initially None, it won't be by the time we check it here.
    # What we can do is re-derive a key value from SECRET_KEY (which is the value django-cryptography uses if
    # CRYPTOGRAPHY_KEY is unset) and check to see if it matches.
    #
    # The below code is based on django_cryptography.conf CryptographyConf.configure()
    backend = settings.CRYPTOGRAPHY_BACKEND
    digest = settings.CRYPTOGRAPHY_DIGEST
    salt = settings.CRYPTOGRAPHY_SALT
    # Key Derivation Function
    kdf = pbkdf2.PBKDF2HMAC(
        algorithm=digest,
        length=digest.digest_size,
        salt=salt,
        iterations=30000,
        backend=backend,
    )
    derived_key = kdf.derive(force_bytes(settings.SECRET_KEY))

    if derived_key == settings.CRYPTOGRAPHY_KEY:
        return [E007]
    return []
