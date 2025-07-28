from django.urls import path

from nautobot.core.views.routers import NautobotUIViewSetRouter
from nautobot.extras.views import ObjectChangeLogView, ObjectDynamicGroupsView, ObjectNotesView
from nautobot.ipam.views import ServiceEditView

from . import views
from .models import VirtualMachine

app_name = "virtualization"

router = NautobotUIViewSetRouter()
router.register("cluster-groups", views.ClusterGroupUIViewSet)
router.register("clusters", views.ClusterUIViewSet)
router.register("cluster-types", views.ClusterTypeUIViewSet)
router.register("interfaces", views.VMInterfaceUIViewSet)

urlpatterns = [
    # Clusters
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
        views.VirtualMachineBulkImportView.as_view(),  # 3.0 TODO: remove, unused
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
    path(  # 3.0 TODO: remove, no longer needed/used since 2.3
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
    path(
        "interfaces/rename/",
        views.VMInterfaceBulkRenameView.as_view(),
        name="vminterface_bulk_rename",
    ),
    path(
        "virtual-machines/interfaces/add/",
        views.VirtualMachineBulkAddInterfaceView.as_view(),
        name="virtualmachine_bulk_add_vminterface",
    ),
]

urlpatterns += router.urls
