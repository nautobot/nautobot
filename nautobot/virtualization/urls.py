from django.urls import path

from nautobot.extras.views import ObjectChangeLogView, ObjectDynamicGroupsView, ObjectNotesView
from nautobot.ipam.views import ServiceEditView
from . import views
from .models import Cluster, ClusterGroup, ClusterType, VirtualMachine, VMInterface

app_name = "virtualization"
urlpatterns = [
    # Cluster types
    path("cluster-types/", views.ClusterTypeListView.as_view(), name="clustertype_list"),
    path(
        "cluster-types/add/",
        views.ClusterTypeEditView.as_view(),
        name="clustertype_add",
    ),
    path(
        "cluster-types/import/",
        views.ClusterTypeBulkImportView.as_view(),
        name="clustertype_import",
    ),
    path(
        "cluster-types/delete/",
        views.ClusterTypeBulkDeleteView.as_view(),
        name="clustertype_bulk_delete",
    ),
    path(
        "cluster-types/<slug:slug>/",
        views.ClusterTypeView.as_view(),
        name="clustertype",
    ),
    path(
        "cluster-types/<slug:slug>/edit/",
        views.ClusterTypeEditView.as_view(),
        name="clustertype_edit",
    ),
    path(
        "cluster-types/<slug:slug>/delete/",
        views.ClusterTypeDeleteView.as_view(),
        name="clustertype_delete",
    ),
    path(
        "cluster-types/<slug:slug>/changelog/",
        ObjectChangeLogView.as_view(),
        name="clustertype_changelog",
        kwargs={"model": ClusterType},
    ),
    path(
        "cluster-types/<slug:slug>/notes/",
        ObjectNotesView.as_view(),
        name="clustertype_notes",
        kwargs={"model": ClusterType},
    ),
    # Cluster groups
    path(
        "cluster-groups/",
        views.ClusterGroupListView.as_view(),
        name="clustergroup_list",
    ),
    path(
        "cluster-groups/add/",
        views.ClusterGroupEditView.as_view(),
        name="clustergroup_add",
    ),
    path(
        "cluster-groups/import/",
        views.ClusterGroupBulkImportView.as_view(),
        name="clustergroup_import",
    ),
    path(
        "cluster-groups/delete/",
        views.ClusterGroupBulkDeleteView.as_view(),
        name="clustergroup_bulk_delete",
    ),
    path(
        "cluster-groups/<slug:slug>/",
        views.ClusterGroupView.as_view(),
        name="clustergroup",
    ),
    path(
        "cluster-groups/<slug:slug>/edit/",
        views.ClusterGroupEditView.as_view(),
        name="clustergroup_edit",
    ),
    path(
        "cluster-groups/<slug:slug>/delete/",
        views.ClusterGroupDeleteView.as_view(),
        name="clustergroup_delete",
    ),
    path(
        "cluster-groups/<slug:slug>/changelog/",
        ObjectChangeLogView.as_view(),
        name="clustergroup_changelog",
        kwargs={"model": ClusterGroup},
    ),
    path(
        "cluster-groups/<slug:slug>/notes/",
        ObjectNotesView.as_view(),
        name="clustergroup_notes",
        kwargs={"model": ClusterGroup},
    ),
    # Clusters
    path("clusters/", views.ClusterListView.as_view(), name="cluster_list"),
    path("clusters/add/", views.ClusterEditView.as_view(), name="cluster_add"),
    path("clusters/import/", views.ClusterBulkImportView.as_view(), name="cluster_import"),
    path("clusters/edit/", views.ClusterBulkEditView.as_view(), name="cluster_bulk_edit"),
    path(
        "clusters/delete/",
        views.ClusterBulkDeleteView.as_view(),
        name="cluster_bulk_delete",
    ),
    path("clusters/<uuid:pk>/", views.ClusterView.as_view(), name="cluster"),
    path("clusters/<uuid:pk>/edit/", views.ClusterEditView.as_view(), name="cluster_edit"),
    path(
        "clusters/<uuid:pk>/delete/",
        views.ClusterDeleteView.as_view(),
        name="cluster_delete",
    ),
    path(
        "clusters/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="cluster_changelog",
        kwargs={"model": Cluster},
    ),
    path(
        "clusters/<uuid:pk>/dynamic-groups/",
        ObjectDynamicGroupsView.as_view(),
        name="cluster_dynamicgroups",
        kwargs={"model": Cluster},
    ),
    path(
        "clusters/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="cluster_notes",
        kwargs={"model": Cluster},
    ),
    path(
        "clusters/<uuid:pk>/devices/add/",
        views.ClusterAddDevicesView.as_view(),
        name="cluster_add_devices",
    ),
    path(
        "clusters/<uuid:pk>/devices/remove/",
        views.ClusterRemoveDevicesView.as_view(),
        name="cluster_remove_devices",
    ),
    # Virtual machines
    path(
        "virtual-machines/",
        views.VirtualMachineListView.as_view(),
        name="virtualmachine_list",
    ),
    path(
        "virtual-machines/add/",
        views.VirtualMachineEditView.as_view(),
        name="virtualmachine_add",
    ),
    path(
        "virtual-machines/import/",
        views.VirtualMachineBulkImportView.as_view(),
        name="virtualmachine_import",
    ),
    path(
        "virtual-machines/edit/",
        views.VirtualMachineBulkEditView.as_view(),
        name="virtualmachine_bulk_edit",
    ),
    path(
        "virtual-machines/delete/",
        views.VirtualMachineBulkDeleteView.as_view(),
        name="virtualmachine_bulk_delete",
    ),
    path(
        "virtual-machines/<uuid:pk>/",
        views.VirtualMachineView.as_view(),
        name="virtualmachine",
    ),
    path(
        "virtual-machines/<uuid:pk>/edit/",
        views.VirtualMachineEditView.as_view(),
        name="virtualmachine_edit",
    ),
    path(
        "virtual-machines/<uuid:pk>/delete/",
        views.VirtualMachineDeleteView.as_view(),
        name="virtualmachine_delete",
    ),
    path(
        "virtual-machines/<uuid:pk>/config-context/",
        views.VirtualMachineConfigContextView.as_view(),
        name="virtualmachine_configcontext",
    ),
    path(
        "virtual-machines/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="virtualmachine_changelog",
        kwargs={"model": VirtualMachine},
    ),
    path(
        "virtual-machines/<uuid:pk>/dynamic-groups/",
        ObjectDynamicGroupsView.as_view(),
        name="virtualmachine_dynamicgroups",
        kwargs={"model": VirtualMachine},
    ),
    path(
        "virtual-machines/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="virtualmachine_notes",
        kwargs={"model": VirtualMachine},
    ),
    path(
        "virtual-machines/<uuid:virtualmachine>/services/assign/",
        ServiceEditView.as_view(),
        name="virtualmachine_service_assign",
    ),
    # VM interfaces
    path("interfaces/", views.VMInterfaceListView.as_view(), name="vminterface_list"),
    path("interfaces/add/", views.VMInterfaceCreateView.as_view(), name="vminterface_add"),
    path(
        "interfaces/import/",
        views.VMInterfaceBulkImportView.as_view(),
        name="vminterface_import",
    ),
    path(
        "interfaces/edit/",
        views.VMInterfaceBulkEditView.as_view(),
        name="vminterface_bulk_edit",
    ),
    path(
        "interfaces/rename/",
        views.VMInterfaceBulkRenameView.as_view(),
        name="vminterface_bulk_rename",
    ),
    path(
        "interfaces/delete/",
        views.VMInterfaceBulkDeleteView.as_view(),
        name="vminterface_bulk_delete",
    ),
    path("interfaces/<uuid:pk>/", views.VMInterfaceView.as_view(), name="vminterface"),
    path(
        "interfaces/<uuid:pk>/edit/",
        views.VMInterfaceEditView.as_view(),
        name="vminterface_edit",
    ),
    path(
        "interfaces/<uuid:pk>/delete/",
        views.VMInterfaceDeleteView.as_view(),
        name="vminterface_delete",
    ),
    path(
        "interfaces/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="vminterface_changelog",
        kwargs={"model": VMInterface},
    ),
    path(
        "interfaces/<uuid:pk>/notes/",
        ObjectNotesView.as_view(),
        name="vminterface_notes",
        kwargs={"model": VMInterface},
    ),
    path(
        "virtual-machines/interfaces/add/",
        views.VirtualMachineBulkAddInterfaceView.as_view(),
        name="virtualmachine_bulk_add_vminterface",
    ),
]
