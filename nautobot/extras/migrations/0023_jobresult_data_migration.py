from django.db import migrations

from nautobot.core.fields import slugify_dots_to_dashes


def migrate_jobresults(apps, schema_editor):
    """
    For all existing JobResults referencing a Job, update them to reference a Job model, creating the model if needed.
    """
    JobResult = apps.get_model("extras", "JobResult")
    Job = apps.get_model("extras", "Job")
    ContentType = apps.get_model("contenttypes", "ContentType")
    job_ct = ContentType.objects.get_by_natural_key("extras", "job")

    for job_jobresult in JobResult.objects.filter(obj_type=job_ct):
        job_classpath = job_jobresult.name
        try:
            source, module_name, job_class_name = job_classpath.split("/")
            job_model, created = Job.objects.get_or_create(
                source=source,
                module_name=module_name,
                job_class_name=job_class_name,
                # AutoSlugField.slugify_function isn't applied during migrations, need to manually generate slug
                slug=slugify_dots_to_dashes(f"{source}-{module_name}-{job_class_name}"),
                defaults={
                    "grouping": module_name,
                    "name": job_class_name,
                    "installed": False,
                    # Since it was previously run, let's assume it's enabled for running
                    "enabled": True,
                },
            )
            if created:
                print(f'Created Job model "{module_name}: {job_class_name}" for {job_classpath}')
            job_jobresult.job_model = job_model
            job_jobresult.save()
        except ValueError:
            # classpath doesn't contain the expected number of slashes? Well, we tried!
            pass


def reverse_migrate_jobresults(apps, schema_editor):
    JobResult = apps.get_model("extras", "JobResult")
    Job = apps.get_model("extras", "Job")
    ContentType = apps.get_model("contenttypes", "ContentType")
    job_ct = ContentType.objects.get_by_natural_key("extras", "job")

    for job_jobresult in JobResult.objects.filter(obj_type=job_ct):
        job_jobresult.job_model = None
        job_jobresult.save()

    Job.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("extras", "0022_job_model"),
    ]

    operations = [
        migrations.RunPython(migrate_jobresults, reverse_migrate_jobresults),
    ]
