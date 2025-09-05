from django.urls import path

from nautobot.core.views.routers import NautobotUIViewSetRouter
from nautobot.extras.views import ObjectChangeLogView, ObjectDynamicGroupsView, ObjectNotesView

from . import views
from .models import (
    IPAddress,
    Prefix,
)

app_name = "ipam"

router = NautobotUIViewSetRouter()
router.register("ip-address-to-interface", views.IPAddressToInterfaceUIViewSet)
router.register("namespaces", views.NamespaceUIViewSet)
router.register("rirs", views.RIRUIViewSet)
router.register("route-targets", views.RouteTargetUIViewSet)
router.register("services", views.ServiceUIViewSet)
router.register("vlans", views.VLANUIViewSet)
router.register("vlan-groups", views.VLANGroupUIViewSet)
router.register("vrfs", views.VRFUIViewSet)

urlpatterns = [
    # Prefixes
    path("prefixes/", views.PrefixListView.as_view(), name="prefix_list"),
    path("prefixes/add/", views.PrefixEditView.as_view(), name="prefix_add"),
    path("prefixes/import/", views.PrefixBulkImportView.as_view(), name="prefix_import"),  # 3.0 TODO: remove, unused
    path("prefixes/edit/", views.PrefixBulkEditView.as_view(), name="prefix_bulk_edit"),
    path(
        "prefixes/delete/",
        views.PrefixBulkDeleteView.as_view(),
        name="prefix_bulk_delete",
    ),
    path("prefixes/<uuid:pk>/", views.PrefixView.as_view(), name="prefix"),
    path("prefixes/<uuid:pk>/edit/", views.PrefixEditView.as_view(), name="prefix_edit"),
    path(
        "prefixes/<uuid:pk>/delete/",
        views.PrefixDeleteView.as_view(),
        name="prefix_delete",
    ),
    path(
        "prefixes/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="prefix_changelog",
        kwargs={"model": Prefix},
    ),
    path(  # 3.0 TODO: remove, no longer needed/used since 2.3
        "prefixes/<uuid:pk>/dynamic-groups/",
        ObjectDynamicGroupsView.as_view(),
        name="prefix_dynamicgroups",
        kwargs={"model": Prefix},
    ),
    path(
        "prefixes/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="prefix_notes",
        kwargs={"model": Prefix},
    ),
    path(
        "prefixes/<uuid:pk>/prefixes/",
        views.PrefixPrefixesView.as_view(),
        name="prefix_prefixes",
    ),
    path(
        "prefixes/<uuid:pk>/ip-addresses/",
        views.PrefixIPAddressesView.as_view(),
        name="prefix_ipaddresses",
    ),
    # IP addresses
    path("ip-addresses/", views.IPAddressListView.as_view(), name="ipaddress_list"),
    path("ip-addresses/add/", views.IPAddressEditView.as_view(), name="ipaddress_add"),
    path(
        "ip-addresses/bulk-add/",
        views.IPAddressBulkCreateView.as_view(),
        name="ipaddress_bulk_add",
    ),
    path(
        "ip-addresses/import/",
        views.IPAddressBulkImportView.as_view(),  # 3.0 TODO: remove, unused
        name="ipaddress_import",
    ),
    path(
        "ip-addresses/edit/",
        views.IPAddressBulkEditView.as_view(),
        name="ipaddress_bulk_edit",
    ),
    path(
        "ip-addresses/merge/",
        views.IPAddressMergeView.as_view(),
        name="ipaddress_merge",
    ),
    path(
        "ip-addresses/delete/",
        views.IPAddressBulkDeleteView.as_view(),
        name="ipaddress_bulk_delete",
    ),
    path(
        "ip-addresses/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="ipaddress_changelog",
        kwargs={"model": IPAddress},
    ),
    path(  # 3.0 TODO: remove, no longer needed/used since 2.3
        "ip-addresses/<uuid:pk>/dynamic-groups/",
        ObjectDynamicGroupsView.as_view(),
        name="ipaddress_dynamicgroups",
        kwargs={"model": IPAddress},
    ),
    path(
        "ip-addresses/<uuid:pk>/interfaces/",
        views.IPAddressInterfacesView.as_view(),
        name="ipaddress_interfaces",
    ),
    path(
        "ip-addresses/<uuid:pk>/vm-interfaces/",
        views.IPAddressVMInterfacesView.as_view(),
        name="ipaddress_vm_interfaces",
    ),
    path(
        "ip-addresses/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="ipaddress_notes",
        kwargs={"model": IPAddress},
    ),
    path(
        "ip-addresses/assign/",
        views.IPAddressAssignView.as_view(),
        name="ipaddress_assign",
    ),
    path("ip-addresses/<uuid:pk>/", views.IPAddressView.as_view(), name="ipaddress"),
    path(
        "ip-addresses/<uuid:pk>/edit/",
        views.IPAddressEditView.as_view(),
        name="ipaddress_edit",
    ),
    path(
        "ip-addresses/<uuid:pk>/delete/",
        views.IPAddressDeleteView.as_view(),
        name="ipaddress_delete",
    ),
]

urlpatterns += router.urls
