from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^vrfs/$', views.VRFListView.as_view(), name='vrf_list'),
    url(r'^vrfs/add/$', views.VRFAddView.as_view(), name='vrf_add'),
    url(r'^vrfs/import/$', views.VRFBulkImportView.as_view(), name='vrf_import'),
    url(r'^vrfs/edit/$', views.VRFBulkEditView.as_view(), name='vrf_bulk_edit'),
    url(r'^vrfs/delete/$', views.VRFBulkDeleteView.as_view(), name='vrf_bulk_delete'),
    url(r'^vrfs/(?P<pk>\d+)/$', views.vrf, name='vrf'),
    url(r'^vrfs/(?P<pk>\d+)/edit/$', views.VRFEditView.as_view(), name='vrf_edit'),
    url(r'^vrfs/(?P<pk>\d+)/delete/$', views.VRFDeleteView.as_view(), name='vrf_delete'),

    url(r'^aggregates/$', views.AggregateListView.as_view(), name='aggregate_list'),
    url(r'^aggregates/add/$', views.AggregateAddView.as_view(), name='aggregate_add'),
    url(r'^aggregates/import/$', views.AggregateBulkImportView.as_view(), name='aggregate_import'),
    url(r'^aggregates/edit/$', views.AggregateBulkEditView.as_view(), name='aggregate_bulk_edit'),
    url(r'^aggregates/delete/$', views.AggregateBulkDeleteView.as_view(), name='aggregate_bulk_delete'),
    url(r'^aggregates/(?P<pk>\d+)/$', views.aggregate, name='aggregate'),
    url(r'^aggregates/(?P<pk>\d+)/edit/$', views.AggregateEditView.as_view(), name='aggregate_edit'),
    url(r'^aggregates/(?P<pk>\d+)/delete/$', views.AggregateDeleteView.as_view(), name='aggregate_delete'),

    url(r'^prefixes/$', views.PrefixListView.as_view(), name='prefix_list'),
    url(r'^prefixes/add/$', views.PrefixAddView.as_view(), name='prefix_add'),
    url(r'^prefixes/import/$', views.PrefixBulkImportView.as_view(), name='prefix_import'),
    url(r'^prefixes/edit/$', views.PrefixBulkEditView.as_view(), name='prefix_bulk_edit'),
    url(r'^prefixes/delete/$', views.PrefixBulkDeleteView.as_view(), name='prefix_bulk_delete'),
    url(r'^prefixes/(?P<pk>\d+)/$', views.prefix, name='prefix'),
    url(r'^prefixes/(?P<pk>\d+)/edit/$', views.PrefixEditView.as_view(), name='prefix_edit'),
    url(r'^prefixes/(?P<pk>\d+)/delete/$', views.PrefixDeleteView.as_view(), name='prefix_delete'),
    url(r'^prefixes/(?P<pk>\d+)/ip-addresses/$', views.prefix_ipaddresses, name='prefix_ipaddresses'),

    url(r'^ip-addresses/$', views.IPAddressListView.as_view(), name='ipaddress_list'),
    url(r'^ip-addresses/add/$', views.IPAddressAddView.as_view(), name='ipaddress_add'),
    url(r'^ip-addresses/import/$', views.IPAddressBulkImportView.as_view(), name='ipaddress_import'),
    url(r'^ip-addresses/edit/$', views.IPAddressBulkEditView.as_view(), name='ipaddress_bulk_edit'),
    url(r'^ip-addresses/delete/$', views.IPAddressBulkDeleteView.as_view(), name='ipaddress_bulk_delete'),
    url(r'^ip-addresses/(?P<pk>\d+)/$', views.ipaddress, name='ipaddress'),
    url(r'^ip-addresses/(?P<pk>\d+)/edit/$', views.IPAddressEditView.as_view(), name='ipaddress_edit'),
    url(r'^ip-addresses/(?P<pk>\d+)/delete/$', views.IPAddressDeleteView.as_view(), name='ipaddress_delete'),

    url(r'^vlans/$', views.VLANListView.as_view(), name='vlan_list'),
    url(r'^vlans/add/$', views.VLANAddView.as_view(), name='vlan_add'),
    url(r'^vlans/import/$', views.VLANBulkImportView.as_view(), name='vlan_import'),
    url(r'^vlans/edit/$', views.VLANBulkEditView.as_view(), name='vlan_bulk_edit'),
    url(r'^vlans/delete/$', views.VLANBulkDeleteView.as_view(), name='vlan_bulk_delete'),
    url(r'^vlans/(?P<pk>\d+)/$', views.vlan, name='vlan'),
    url(r'^vlans/(?P<pk>\d+)/edit/$', views.VLANEditView.as_view(), name='vlan_edit'),
    url(r'^vlans/(?P<pk>\d+)/delete/$', views.VLANDeleteView.as_view(), name='vlan_delete'),
]
