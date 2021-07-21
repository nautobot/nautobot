from nautobot.core.apps import HomePageItem, HomePagePanel

from .models import DummyModel


def get_dummy_data(request):
    examples = DummyModel.objects.all()
    if not examples:
        examples = (
            DummyModel.objects.create(name="Example 1", number=100),
            DummyModel.objects.create(name="Example 2", number=200),
            DummyModel.objects.create(name="Example 3", number=300),
        )
    return examples


layout = (
    HomePagePanel(
        name="Organization",
        items=(
            HomePageItem(
                name="Dummy Models",
                model=DummyModel,
                weight=150,
                link="plugins:dummy_plugin:dummymodel_list",
                description="List dummy plugin models.",
                permissions=["dummy_plugin.view_dummymodel"],
            ),
            HomePageItem(
                name="Sites",
                permissions=["dcim.view_site"],
                custom_template="panel_dummy_example.html",
            ),
        ),
    ),
    HomePagePanel(
        name="Dummy Plugin",
        weight=250,
        items=(
            HomePageItem(
                name="Dummy Models",
                link="plugins:dummy_plugin:dummymodel_list",
                model=DummyModel,
                description="List dummy plugin models.",
                permissions=["dummy_plugin.view_dummymodel"],
                weight=100,
            ),
        ),
    ),
    HomePagePanel(
        name="Custom Dummy Plugin",
        custom_template="panel_dummy_example.html",
        custom_data={"dummy_data": get_dummy_data},
        permissions=["dummy_plugin.view_dummymodel"],
        weight=350,
    ),
)
