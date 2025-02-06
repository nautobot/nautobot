from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("nautobot_data_validation_engine", "0003_datacompliance"),
    ]

    operations = [
        migrations.AlterField(
            model_name="datacompliance",
            name="created",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name="regularexpressionvalidationrule",
            name="created",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name="minmaxvalidationrule",
            name="created",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name="requiredvalidationrule",
            name="created",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name="uniquevalidationrule",
            name="created",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
    ]
