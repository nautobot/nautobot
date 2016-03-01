from django.conf.urls import url

from .views import *


urlpatterns = [

    # Secrets
    url(r'^secrets/$', SecretListView.as_view(), name='secret_list'),
    url(r'^secrets/(?P<pk>\d+)/$', SecretDetailView.as_view(), name='secret_detail'),
    url(r'^secrets/(?P<pk>\d+)/decrypt/$', SecretDecryptView.as_view(), name='secret_decrypt'),

    # Secret roles
    url(r'^secret-roles/$', SecretRoleListView.as_view(), name='secretrole_list'),
    url(r'^secret-roles/(?P<pk>\d+)/$', SecretRoleDetailView.as_view(), name='secretrole_detail'),

    # Miscellaneous
    url(r'^generate-keys/$', RSAKeyGeneratorView.as_view(), name='generate_keys'),

]
