from Crypto.PublicKey import RSA

from django.shortcuts import get_object_or_404

from rest_framework import generics
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView

from extras.api.renderers import FreeRADIUSClientsRenderer
from secrets.filters import SecretFilter
from secrets.models import Secret, SecretRole, UserKey
from .serializers import SecretRoleSerializer, SecretSerializer


ERR_USERKEY_MISSING = "No UserKey found for the current user."
ERR_USERKEY_INACTIVE = "UserKey has not been activated for decryption."
ERR_PRIVKEY_INVALID = "Invalid private key."


class SecretViewPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm('secrets.view_secret')


class SecretRoleListView(generics.ListAPIView):
    """
    List all secret roles
    """
    queryset = SecretRole.objects.all()
    serializer_class = SecretRoleSerializer


class SecretRoleDetailView(generics.RetrieveAPIView):
    """
    Retrieve a single secret role
    """
    queryset = SecretRole.objects.all()
    serializer_class = SecretRoleSerializer


class SecretListView(generics.GenericAPIView):
    """
    List secrets (filterable). If a private key is POSTed, attempt to decrypt each Secret.
    """
    queryset = Secret.objects.select_related('device', 'role')
    serializer_class = SecretSerializer
    filter_class = SecretFilter
    permission_classes = [SecretViewPermission]
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES + [FreeRADIUSClientsRenderer]

    def get(self, request, private_key=None, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Attempt to decrypt each Secret if a private key was provided.
        if private_key is not None:
            try:
                uk = UserKey.objects.get(user=request.user)
            except UserKey.DoesNotExist:
                return Response(
                    {'error': ERR_USERKEY_MISSING},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not uk.is_active():
                return Response(
                    {'error': ERR_USERKEY_INACTIVE},
                    status=status.HTTP_400_BAD_REQUEST
                )
            master_key = uk.get_master_key(private_key)
            if master_key is not None:
                for s in queryset:
                    s.decrypt(master_key)
            else:
                return Response(
                    {'error': ERR_PRIVKEY_INVALID},
                    status=status.HTTP_400_BAD_REQUEST
                )

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        private_key = request.POST.get('private_key')
        return self.get(request, private_key=private_key)


class SecretDetailView(generics.GenericAPIView):
    """
    Retrieve a single Secret. If a private key is POSTed, attempt to decrypt the Secret.
    """
    queryset = Secret.objects.select_related('device', 'role')
    serializer_class = SecretSerializer
    permission_classes = [SecretViewPermission]
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES + [FreeRADIUSClientsRenderer]

    def get(self, request, pk, private_key=None, *args, **kwargs):
        secret = get_object_or_404(Secret, pk=pk)

        # Attempt to decrypt the Secret if a private key was provided.
        if private_key is not None:
            try:
                uk = UserKey.objects.get(user=request.user)
            except UserKey.DoesNotExist:
                return Response(
                    {'error': ERR_USERKEY_MISSING},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not uk.is_active():
                return Response(
                    {'error': ERR_USERKEY_INACTIVE},
                    status=status.HTTP_400_BAD_REQUEST
                )
            master_key = uk.get_master_key(private_key)
            if master_key is not None:
                secret.decrypt(master_key)
            else:
                return Response(
                    {'error': ERR_PRIVKEY_INVALID},
                    status=status.HTTP_400_BAD_REQUEST
                )

        serializer = self.get_serializer(secret)
        return Response(serializer.data)

    def post(self, request, pk, *args, **kwargs):
        private_key = request.POST.get('private_key')
        return self.get(request, pk, private_key=private_key)


class RSAKeyGeneratorView(APIView):
    """
    Generate a new RSA key pair for a user. Authenticated because it's a ripe avenue for DoS.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):

        # Determine what size key to generate
        key_size = request.GET.get('key_size', 2048)
        if key_size not in range(2048, 4097, 256):
            key_size = 2048

        # Export RSA private and public keys in PEM format
        key = RSA.generate(key_size)
        private_key = key.exportKey('PEM')
        public_key = key.publickey().exportKey('PEM')

        return Response({
            'private_key': private_key,
            'public_key': public_key,
        })
