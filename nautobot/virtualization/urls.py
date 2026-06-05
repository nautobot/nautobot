from django.urls import path

from nautobot.core.views.routers import NautobotUIViewSetRouter

from . import views

app_name = "virtualization"

router = NautobotUIViewSetRouter()
router.register("cluster-groups", views.ClusterGroupUIViewSet)
router.register("clusters", views.ClusterUIViewSet)
router.register("cluster-types", views.ClusterTypeUIViewSet)
router.register("interfaces", views.VMInterfaceUIViewSet)
router.register("virtual-machines", views.VirtualMachineUIViewSet)

urlpatterns = [
    path(
        "virtual-machines/interfaces/add/",
        views.VirtualMachineBulkAddInterfaceView.as_view(),
        name="virtualmachine_bulk_add_vminterface",
    ),
]

urlpatterns += router.urls
