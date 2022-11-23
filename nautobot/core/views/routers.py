from rest_framework.routers import Route, SimpleRouter


class NautobotUIViewSetRouter(SimpleRouter):
    """
    Nautobot Custom Router that is intended for UI use only.
    """

    routes = [
        Route(
            url=r"^{prefix}/$",
            mapping={"get": "list"},
            name="{basename}_list",
            detail=False,
            initkwargs={"suffix": "List"},
        ),
        Route(
            url=r"^{prefix}/add/$",
            mapping={
                "get": "create",
                "post": "create",
            },
            name="{basename}_add",
            detail=False,
            initkwargs={"suffix": "Add"},
        ),
        Route(
            url=r"^{prefix}/import/$",
            mapping={
                "get": "bulk_create",
                "post": "bulk_create",
            },
            name="{basename}_import",
            detail=False,
            initkwargs={"suffix": "Import"},
        ),
        Route(
            url=r"^{prefix}/edit/$",
            mapping={
                "post": "bulk_update",
            },
            name="{basename}_bulk_edit",
            detail=False,
            initkwargs={"suffix": "Bulk Edit"},
        ),
        Route(
            url=r"^{prefix}/delete/$",
            mapping={
                "post": "bulk_destroy",
            },
            name="{basename}_bulk_delete",
            detail=False,
            initkwargs={"suffix": "Bulk Delete"},
        ),
        Route(
            url=r"^{prefix}/{lookup}$",
            mapping={"get": "retrieve"},
            name="{basename}",
            detail=True,
            initkwargs={"suffix": "Detail"},
        ),
        Route(
            url=r"^{prefix}/{lookup}/delete/$",
            mapping={
                "get": "destroy",
                "post": "destroy",
            },
            name="{basename}_delete",
            detail=True,
            initkwargs={"suffix": "Delete"},
        ),
        Route(
            url=r"^{prefix}/{lookup}/edit/$",
            mapping={
                "get": "update",
                "post": "update",
            },
            name="{basename}_edit",
            detail=True,
            initkwargs={"suffix": "Edit"},
        ),
        Route(
            url=r"^{prefix}/{lookup}/changelog/$",
            mapping={
                "get": "changelog",
            },
            name="{basename}_changelog",
            detail=True,
            initkwargs={"suffix": "Changelog"},
        ),
        Route(
            url=r"^{prefix}/{lookup}/notes/$",
            mapping={
                "get": "notes",
            },
            name="{basename}_notes",
            detail=True,
            initkwargs={"suffix": "Notes"},
        ),
    ]
