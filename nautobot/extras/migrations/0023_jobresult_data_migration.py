from django.db import migrations


def migrate_jobresults(apps, schema_editor):
    """
    For all existing JobResults referencing a Job, update them to reference a JobModel, creating the JobModel if needed.
    """
    JobResult = apps.get_model("extras", "JobResult")
    JobModel = apps.get_model("extras", "JobModel")
    ContentType = apps.get_model("contenttypes", "ContentType")
    job_ct = ContentType.objects.get_by_natural_key("extras", "job")

    for job_jobresult in JobResult.objects.filter(obj_type=job_ct):
        job_classpath = job_jobresult.name
        try:
            source, module, job_class = job_classpath.split("/")
            if source.startswith("git."):
                source, repo_slug = source.split(".", 1)
                module = f"{repo_slug}/{module}"
            job_model, created = JobModel.objects.get_or_create(
                source=source,
                module=module,
                job_class=job_class,
                defaults={
                    "grouping": module,
                    "name": job_class,
                    "installed": False,
                    # Since it was previously run, let's assume it's enabled for running
                    "enabled": True,
                },
            )
            if created:
                print(
                    f'Created JobModel "{module}: {job_class}" for Jobs associated with JobResults for {job_classpath}'
                )
            job_jobresult.job_model = job_model
            job_jobresult.save()
        except ValueError:
            # classpath doesn't contain the expected number of slashes? Well, we tried!
            pass


def reverse_migrate_jobresults(apps, schema_editor):
    JobResult = apps.get_model("extras", "JobResult")
    JobModel = apps.get_model("extras", "JobModel")
    ContentType = apps.get_model("contenttypes", "ContentType")
    job_ct = ContentType.objects.get_by_natural_key("extras", "job")

    for job_jobresult in JobResult.objects.filter(obj_type=job_ct):
        job_jobresult.job_model = None
        job_jobresult.save()

    JobModel.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("extras", "0022_job_model"),
    ]

    operations = [
        migrations.RunPython(migrate_jobresults, reverse_migrate_jobresults),
    ]
