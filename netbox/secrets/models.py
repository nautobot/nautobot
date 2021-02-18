import os

from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from taggit.managers import TaggableManager

from extras.models import ChangeLoggedModel, CustomFieldModel, TaggedItem
from extras.utils import extras_features
from utilities.querysets import RestrictedQuerySet


__all__ = (
    'Secret',
    'SecretRole',
    'SessionKey',
    'UserKey',
)


class UserKey(models.Model):
    """
    A UserKey stores a user's personal RSA (public) encryption key, which is used to generate their unique encrypted
    copy of the master encryption key. The encrypted instance of the master key can be decrypted only with the user's
    matching (private) decryption key.
    """
    created = models.DateField(
        auto_now_add=True
    )
    last_updated = models.DateTimeField(
        auto_now=True
    )
    user = models.OneToOneField(
        to=User,
        on_delete=models.CASCADE,
        related_name='user_key',
        editable=False
    )
    public_key = models.TextField(
        verbose_name='RSA public key'
    )
    master_key_cipher = models.BinaryField(
        max_length=512,
        blank=True,
        null=True,
        editable=False
    )

    # objects = UserKeyQuerySet.as_manager()

    class Meta:
        ordering = ['user__username']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Store the initial public_key and master_key_cipher to check for changes on save().
        self.__initial_public_key = self.public_key
        self.__initial_master_key_cipher = self.master_key_cipher

    def __str__(self):
        return self.user.username


class SessionKey(models.Model):
    """
    A SessionKey stores a User's temporary key to be used for the encryption and decryption of secrets.
    """
    userkey = models.OneToOneField(
        to='secrets.UserKey',
        on_delete=models.CASCADE,
        related_name='session_key',
        editable=False
    )
    cipher = models.BinaryField(
        max_length=512,
        editable=False
    )
    hash = models.CharField(
        max_length=128,
        editable=False
    )
    created = models.DateTimeField(
        auto_now_add=True
    )

    key = None

    class Meta:
        ordering = ['userkey__user__username']

    def __str__(self):
        return self.userkey.user.username


class SecretRole(ChangeLoggedModel):
    """
    A SecretRole represents an arbitrary functional classification of Secrets. For example, a user might define roles
    such as "Login Credentials" or "SNMP Communities."
    """
    name = models.CharField(
        max_length=100,
        unique=True
    )
    slug = models.SlugField(
        max_length=100,
        unique=True
    )
    description = models.CharField(
        max_length=200,
        blank=True,
    )

    objects = RestrictedQuerySet.as_manager()

    csv_headers = ['name', 'slug', 'description']

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return "{}?role={}".format(reverse('secrets:secret_list'), self.slug)

    def to_csv(self):
        return (
            self.name,
            self.slug,
            self.description,
        )


@extras_features(
    'custom_fields',
    'custom_links',
    'export_templates',
    'webhooks'
)
class Secret(ChangeLoggedModel, CustomFieldModel):
    """
    A Secret stores an AES256-encrypted copy of sensitive data, such as passwords or secret keys. An irreversible
    SHA-256 hash is stored along with the ciphertext for validation upon decryption. Each Secret is assigned to exactly
    one NetBox object, and objects may have multiple Secrets associated with them. A name can optionally be defined
    along with the ciphertext; this string is stored as plain text in the database.

    A Secret can be up to 65,535 bytes (64KB - 1B) in length. Each secret string will be padded with random data to
    a minimum of 64 bytes during encryption in order to protect short strings from ciphertext analysis.
    """
    assigned_object_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.PROTECT
    )
    assigned_object_id = models.PositiveIntegerField()
    assigned_object = GenericForeignKey(
        ct_field='assigned_object_type',
        fk_field='assigned_object_id'
    )
    role = models.ForeignKey(
        to='secrets.SecretRole',
        on_delete=models.PROTECT,
        related_name='secrets'
    )
    name = models.CharField(
        max_length=100,
        blank=True
    )
    ciphertext = models.BinaryField(
        max_length=65568,  # 128-bit IV + 16-bit pad length + 65535B secret + 15B padding
        editable=False
    )
    hash = models.CharField(
        max_length=128,
        editable=False
    )
    tags = TaggableManager(through=TaggedItem)

    objects = RestrictedQuerySet.as_manager()

    plaintext = None
    csv_headers = ['assigned_object_type', 'assigned_object_id', 'role', 'name', 'plaintext']

    class Meta:
        ordering = ('role', 'name', 'pk')
        unique_together = ('assigned_object_type', 'assigned_object_id', 'role', 'name')

    def __init__(self, *args, **kwargs):
        self.plaintext = kwargs.pop('plaintext', None)
        super().__init__(*args, **kwargs)

    def __str__(self):
        return self.name or 'Secret'
