# Generated by Django 3.2.24 on 2024-02-29 07:45

from django.db import migrations, models

import nautobot.core.models.fields


class Migration(migrations.Migration):
    dependencies = [
        ("extras", "0104_contact_contactassociation_team"),
    ]

    operations = [
        migrations.AlterField(
            model_name="computedfield",
            name="description",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="computedfield",
            name="key",
            field=nautobot.core.models.fields.AutoSlugField(
                blank=True, max_length=255, populate_from="label", unique=True
            ),
        ),
        migrations.AlterField(
            model_name="computedfield",
            name="label",
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name="configcontext",
            name="description",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="configcontext",
            name="name",
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name="configcontextschema",
            name="description",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="configcontextschema",
            name="name",
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name="contact",
            name="name",
            field=models.CharField(db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="contact",
            name="phone",
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="customfield",
            name="description",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="customfield",
            name="key",
            field=nautobot.core.models.fields.AutoSlugField(
                blank=True, max_length=255, populate_from="label", separator="_", unique=True
            ),
        ),
        migrations.AlterField(
            model_name="customfield",
            name="label",
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name="customfieldchoice",
            name="value",
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name="customlink",
            name="group_name",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="customlink",
            name="name",
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name="dynamicgroup",
            name="description",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="dynamicgroup",
            name="name",
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name="exporttemplate",
            name="description",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="exporttemplate",
            name="file_extension",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="exporttemplate",
            name="mime_type",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="exporttemplate",
            name="name",
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name="gitrepository",
            name="branch",
            field=models.CharField(default="main", max_length=255),
        ),
        migrations.AlterField(
            model_name="gitrepository",
            name="name",
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name="gitrepository",
            name="slug",
            field=nautobot.core.models.fields.AutoSlugField(
                blank=True, max_length=255, populate_from="name", unique=True
            ),
        ),
        migrations.AlterField(
            model_name="graphqlquery",
            name="name",
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name="healthchecktestmodel",
            name="title",
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name="imageattachment",
            name="name",
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="job",
            name="task_queues",
            field=nautobot.core.models.fields.JSONArrayField(
                base_field=models.CharField(blank=True, max_length=255), blank=True, default=list
            ),
        ),
        migrations.AlterField(
            model_name="jobbutton",
            name="group_name",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="jobbutton",
            name="name",
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name="jobhook",
            name="name",
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name="relationship",
            name="description",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="relationship",
            name="destination_label",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="relationship",
            name="key",
            field=nautobot.core.models.fields.AutoSlugField(
                blank=True, max_length=255, populate_from="label", unique=True
            ),
        ),
        migrations.AlterField(
            model_name="relationship",
            name="label",
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name="relationship",
            name="source_label",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="role",
            name="description",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="role",
            name="name",
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name="scheduledjob",
            name="name",
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name="scheduledjob",
            name="queue",
            field=models.CharField(blank=True, db_index=True, default="", max_length=255),
        ),
        migrations.AlterField(
            model_name="secret",
            name="description",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="secret",
            name="name",
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name="secret",
            name="provider",
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name="secretsgroup",
            name="description",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="secretsgroup",
            name="name",
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name="status",
            name="description",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="status",
            name="name",
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name="tag",
            name="description",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="tag",
            name="name",
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name="team",
            name="name",
            field=models.CharField(db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="team",
            name="phone",
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="webhook",
            name="http_content_type",
            field=models.CharField(default="application/json", max_length=255),
        ),
        migrations.AlterField(
            model_name="webhook",
            name="name",
            field=models.CharField(max_length=255, unique=True),
        ),
    ]