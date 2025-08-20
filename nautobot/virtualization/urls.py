from django.urls import path

from nautobot.core.views.routers import NautobotUIViewSetRouter
from nautobot.extras.views import ObjectChangeLogView, ObjectNotesView
from nautobot.ipam.views import ServiceEditView

from . import views
from .models import VMInterface

app_name = "virtualization"

router = NautobotUIViewSetRouter()
router.register("cluster-groups", views.ClusterGroupUIViewSet)
router.register("clusters", views.ClusterUIViewSet)
router.register("cluster-types", views.ClusterTypeUIViewSet)
router.register("virtual-machines", views.VirtualMachineUIViewSet)

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
        "virtual-machines/<uuid:pk>/config-context/",
        views.VirtualMachineConfigContextView.as_view(),
        name="virtualmachine_configcontext",
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
        views.VMInterfaceBulkImportView.as_view(),  # 3.0 TODO: remove, unused
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

urlpatterns += router.urls
