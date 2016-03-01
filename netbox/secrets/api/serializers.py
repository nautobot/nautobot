from rest_framework import serializers

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

# TODO: Serialize parent info
class SecretSerializer(serializers.ModelSerializer):
    role = SecretRoleNestedSerializer()

    class Meta:
        model = Secret
        fields = ['id', 'role', 'name', 'hash', 'created', 'last_modified']


class SecretNestedSerializer(SecretSerializer):

    class Meta(SecretSerializer.Meta):
        fields = ['id', 'name']
