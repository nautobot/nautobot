from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^circuits/$', views.circuit_list, name='circuit_list'),
    url(r'^circuits/add/$', views.circuit_add, name='circuit_add'),
    url(r'^circuits/import/$', views.CircuitBulkImportView.as_view(), name='circuit_import'),
    url(r'^circuits/edit/$', views.CircuitBulkEditView.as_view(), name='circuit_bulk_edit'),
    url(r'^circuits/delete/$', views.CircuitBulkDeleteView.as_view(), name='circuit_bulk_delete'),
    url(r'^circuits/(?P<pk>\d+)/$', views.circuit, name='circuit'),
    url(r'^circuits/(?P<pk>\d+)/edit/$', views.circuit_edit, name='circuit_edit'),
    url(r'^circuits/(?P<pk>\d+)/delete/$', views.circuit_delete, name='circuit_delete'),

    url(r'^providers/$', views.provider_list, name='provider_list'),
    url(r'^providers/add/$', views.provider_add, name='provider_add'),
    url(r'^providers/import/$', views.ProviderBulkImportView.as_view(), name='provider_import'),
    url(r'^providers/edit/$', views.ProviderBulkEditView.as_view(), name='provider_bulk_edit'),
    url(r'^providers/delete/$', views.ProviderBulkDeleteView.as_view(), name='provider_bulk_delete'),
    url(r'^providers/(?P<slug>[\w-]+)/$', views.provider, name='provider'),
    url(r'^providers/(?P<slug>[\w-]+)/edit/$', views.provider_edit, name='provider_edit'),
    url(r'^providers/(?P<slug>[\w-]+)/delete/$', views.provider_delete, name='provider_delete'),
]
