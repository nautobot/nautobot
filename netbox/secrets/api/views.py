from Crypto.PublicKey import RSA

from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404

from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from secrets.models import Secret, SecretRole, UserKey
from .serializers import SecretRoleSerializer, SecretSerializer


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


class SecretListView(generics.ListAPIView):
    """
    List secrets (filterable)
    """
    queryset = Secret.objects.select_related('role')
    serializer_class = SecretSerializer
    #filter_class = SecretFilter
    permission_classes = [IsAuthenticated]


class SecretDetailView(generics.RetrieveAPIView):
    """
    Retrieve a single Secret
    """
    queryset = Secret.objects.select_related('role')
    serializer_class = SecretSerializer
    permission_classes = [IsAuthenticated]


class SecretDecryptView(APIView):
    """
    Retrieve the plaintext from a stored Secret. The request must include a valid private key.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):

        secret = get_object_or_404(Secret, pk=pk)
        private_key = request.POST.get('private_key')
        if not private_key:
            raise ValidationError("Private key is missing from request.")

        # Retrieve the Secret's plaintext with the user's private key
        try:
            uk = UserKey.objects.get(user=request.user)
        except UserKey.DoesNotExist:
            return HttpResponseForbidden(reason="No UserKey found.")
        if not uk.is_active():
            return HttpResponseForbidden(reason="UserKey is inactive.")

        # Attempt to decrypt the Secret.
        master_key = uk.get_master_key(private_key)
        if master_key is None:
            return HttpResponseForbidden(reason="Invalid secret key.")
        secret.decrypt(master_key)

        return Response({
            'plaintext': secret.plaintext,
        })


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
