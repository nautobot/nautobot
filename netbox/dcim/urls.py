from django.conf.urls import url

from secrets.views import secret_add

from . import views

urlpatterns = [

    # Sites
    url(r'^sites/$', views.SiteListView.as_view(), name='site_list'),
    url(r'^sites/add/$', views.site_add, name='site_add'),
    url(r'^sites/import/$', views.SiteBulkImportView.as_view(), name='site_import'),
    url(r'^sites/(?P<slug>[\w-]+)/$', views.site, name='site'),
    url(r'^sites/(?P<slug>[\w-]+)/edit/$', views.site_edit, name='site_edit'),
    url(r'^sites/(?P<slug>[\w-]+)/delete/$', views.site_delete, name='site_delete'),

    # Racks
    url(r'^racks/$', views.RackListView.as_view(), name='rack_list'),
    url(r'^racks/add/$', views.rack_add, name='rack_add'),
    url(r'^racks/import/$', views.RackBulkImportView.as_view(), name='rack_import'),
    url(r'^racks/edit/$', views.RackBulkEditView.as_view(), name='rack_bulk_edit'),
    url(r'^racks/delete/$', views.RackBulkDeleteView.as_view(), name='rack_bulk_delete'),
    url(r'^racks/(?P<pk>\d+)/$', views.rack, name='rack'),
    url(r'^racks/(?P<pk>\d+)/edit/$', views.rack_edit, name='rack_edit'),
    url(r'^racks/(?P<pk>\d+)/delete/$', views.rack_delete, name='rack_delete'),

    # Devices
    url(r'^devices/$', views.DeviceListView.as_view(), name='device_list'),
    url(r'^devices/add/$', views.device_add, name='device_add'),
    url(r'^devices/import/$', views.DeviceBulkImportView.as_view(), name='device_import'),
    url(r'^devices/edit/$', views.DeviceBulkEditView.as_view(), name='device_bulk_edit'),
    url(r'^devices/delete/$', views.DeviceBulkDeleteView.as_view(), name='device_bulk_delete'),
    url(r'^devices/(?P<pk>\d+)/$', views.device, name='device'),
    url(r'^devices/(?P<pk>\d+)/edit/$', views.device_edit, name='device_edit'),
    url(r'^devices/(?P<pk>\d+)/delete/$', views.device_delete, name='device_delete'),
    url(r'^devices/(?P<pk>\d+)/inventory/$', views.device_inventory, name='device_inventory'),
    url(r'^devices/(?P<pk>\d+)/lldp-neighbors/$', views.device_lldp_neighbors, name='device_lldp_neighbors'),
    url(r'^devices/(?P<pk>\d+)/ip-addresses/assign/$', views.ipaddress_assign, name='ipaddress_assign'),
    url(r'^devices/(?P<parent_pk>\d+)/add-secret/$', secret_add, {'parent_model': 'dcim.Device'},
        name='device_addsecret'),

    # Console ports
    url(r'^devices/(?P<pk>\d+)/console-ports/add/$', views.consoleport_add, name='consoleport_add'),
    url(r'^console-ports/(?P<pk>\d+)/connect/$', views.consoleport_connect, name='consoleport_connect'),
    url(r'^console-ports/(?P<pk>\d+)/disconnect/$', views.consoleport_disconnect, name='consoleport_disconnect'),
    url(r'^console-ports/(?P<pk>\d+)/edit/$', views.consoleport_edit, name='consoleport_edit'),
    url(r'^console-ports/(?P<pk>\d+)/delete/$', views.consoleport_delete, name='consoleport_delete'),

    # Console server ports
    url(r'^devices/(?P<pk>\d+)/console-server-ports/add/$', views.consoleserverport_add, name='consoleserverport_add'),
    url(r'^console-server-ports/(?P<pk>\d+)/connect/$', views.consoleserverport_connect, name='consoleserverport_connect'),
    url(r'^console-server-ports/(?P<pk>\d+)/disconnect/$', views.consoleserverport_disconnect, name='consoleserverport_disconnect'),
    url(r'^console-server-ports/(?P<pk>\d+)/edit/$', views.consoleserverport_edit, name='consoleserverport_edit'),
    url(r'^console-server-ports/(?P<pk>\d+)/delete/$', views.consoleserverport_delete, name='consoleserverport_delete'),

    # Power ports
    url(r'^devices/(?P<pk>\d+)/power-ports/add/$', views.powerport_add, name='powerport_add'),
    url(r'^power-ports/(?P<pk>\d+)/connect/$', views.powerport_connect, name='powerport_connect'),
    url(r'^power-ports/(?P<pk>\d+)/disconnect/$', views.powerport_disconnect, name='powerport_disconnect'),
    url(r'^power-ports/(?P<pk>\d+)/edit/$', views.powerport_edit, name='powerport_edit'),
    url(r'^power-ports/(?P<pk>\d+)/delete/$', views.powerport_delete, name='powerport_delete'),

    # Power outlets
    url(r'^devices/(?P<pk>\d+)/power-outlets/add/$', views.poweroutlet_add, name='poweroutlet_add'),
    url(r'^power-outlets/(?P<pk>\d+)/connect/$', views.poweroutlet_connect, name='poweroutlet_connect'),
    url(r'^power-outlets/(?P<pk>\d+)/disconnect/$', views.poweroutlet_disconnect, name='poweroutlet_disconnect'),
    url(r'^power-outlets/(?P<pk>\d+)/edit/$', views.poweroutlet_edit, name='poweroutlet_edit'),
    url(r'^power-outlets/(?P<pk>\d+)/delete/$', views.poweroutlet_delete, name='poweroutlet_delete'),

    # Console/power/interface connections
    url(r'^console-connections/$', views.ConsoleConnectionsListView.as_view(), name='console_connections_list'),
    url(r'^console-connections/import/$', views.ConsoleConnectionsBulkImportView.as_view(), name='console_connections_import'),
    url(r'^power-connections/$', views.PowerConnectionsListView.as_view(), name='power_connections_list'),
    url(r'^power-connections/import/$', views.PowerConnectionsBulkImportView.as_view(), name='power_connections_import'),
    url(r'^interface-connections/$', views.InterfaceConnectionsListView.as_view(), name='interface_connections_list'),
    url(r'^interface-connections/import/$', views.InterfaceConnectionsBulkImportView.as_view(), name='interface_connections_import'),

    # Interfaces
    url(r'^devices/interfaces/add/$', views.InterfaceBulkAddView.as_view(), name='interface_bulk_add'),
    url(r'^devices/(?P<pk>\d+)/interfaces/add/$', views.interface_add, name='interface_add'),
    url(r'^devices/(?P<pk>\d+)/interface-connections/add/$', views.interfaceconnection_add, name='interfaceconnection_add'),
    url(r'^interface-connections/(?P<pk>\d+)/delete/$', views.interfaceconnection_delete, name='interfaceconnection_delete'),
    url(r'^interfaces/(?P<pk>\d+)/edit/$', views.interface_edit, name='interface_edit'),
    url(r'^interfaces/(?P<pk>\d+)/delete/$', views.interface_delete, name='interface_delete'),

]
