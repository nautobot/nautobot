from nautobot.core.apps import HomePageItem, HomePagePanel

from .models import ExampleModel


def get_example_data(request):
    examples = ExampleModel.objects.all()
    if not examples:
        examples = (
            ExampleModel.objects.create(name="Example 1", number=100),
            ExampleModel.objects.create(name="Example 2", number=200),
            ExampleModel.objects.create(name="Example 3", number=300),
        )
    return examples


layout = (
    HomePagePanel(
        name="Organization",
        items=(
            HomePageItem(
                name="Example Models",
                model=ExampleModel,
                weight=150,
                link="plugins:example_plugin:examplemodel_list",
                description="List example plugin models.",
                permissions=["example_plugin.view_examplemodel"],
            ),
        ),
    ),
    HomePagePanel(
        name="Example Plugin",
        weight=250,
        items=(
            HomePageItem(
                name="Custom Example Plugin",
                custom_template="item_example.html",
                custom_data={"example_data": get_example_data},
                permissions=["example_plugin.view_examplemodel"],
                weight=100,
            ),
        ),
    ),
    HomePagePanel(
        name="Custom Example Plugin",
        custom_template="panel_example.html",
        custom_data={"example_data": get_example_data},
        permissions=["example_plugin.view_examplemodel"],
        weight=350,
    ),
)
