from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0010_user_default_saved_views"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="objectpermission",
            options={"ordering": ["name"]},
        ),
    ]
