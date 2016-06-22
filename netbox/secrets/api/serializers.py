from rest_framework import serializers

from dcim.models import Device
from ipam.api.serializers import IPAddressNestedSerializer
from secrets.models import Secret, SecretRole


#
# SecretRoles
#

class SecretRoleSerializer(serializers.ModelSerializer):

    class Meta:
        model = SecretRole
        fields = ['id', 'name', 'slug']


class SecretRoleNestedSerializer(SecretRoleSerializer):

    class Meta(SecretRoleSerializer.Meta):
        pass


#
# Secrets
#

class SecretDeviceSerializer(serializers.ModelSerializer):
    primary_ip = IPAddressNestedSerializer()

    class Meta:
        model = Device
        fields = ['id', 'name', 'primary_ip']


class SecretSerializer(serializers.ModelSerializer):
    device = SecretDeviceSerializer()
    role = SecretRoleNestedSerializer()

    class Meta:
        model = Secret
        fields = ['id', 'device', 'role', 'name', 'plaintext', 'hash', 'created', 'last_updated']


class SecretNestedSerializer(SecretSerializer):

    class Meta(SecretSerializer.Meta):
        fields = ['id', 'name']
