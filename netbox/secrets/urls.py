from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^secrets/$', views.secret_list, name='secret_list'),
    url(r'^secrets/import/$', views.secret_import, name='secret_import'),
    url(r'^secrets/edit/$', views.SecretBulkEditView.as_view(), name='secret_bulk_edit'),
    url(r'^secrets/delete/$', views.SecretBulkDeleteView.as_view(), name='secret_bulk_delete'),
    url(r'^secrets/(?P<pk>\d+)/$', views.secret, name='secret'),
    url(r'^secrets/(?P<pk>\d+)/edit/$', views.secret_edit, name='secret_edit'),
    url(r'^secrets/(?P<pk>\d+)/delete/$', views.secret_delete, name='secret_delete'),
]
