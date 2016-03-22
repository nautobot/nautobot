from rest_framework import serializers

from dcim.api.serializers import DeviceNestedSerializer
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

class SecretSerializer(serializers.ModelSerializer):
    device = DeviceNestedSerializer()
    role = SecretRoleNestedSerializer()

    class Meta:
        model = Secret
        fields = ['id', 'device', 'role', 'name', 'plaintext', 'hash', 'created', 'last_modified']


class SecretNestedSerializer(SecretSerializer):

    class Meta(SecretSerializer.Meta):
        fields = ['id', 'name']
