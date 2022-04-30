from django.db import migrations

from nautobot.core.fields import slugify_dots_to_dashes


def _create_job_model(job_model_class, class_path):
    try:
        source, module_name, job_class_name = class_path.split("/")
        # At this point in the migrations, source = "git.RepositoryName" not just "git", so not JOB_MAX_SOURCE_LENGTH
        if len(source) > 110:
            print(f'Skipping Job model creation from "{class_path}" as the source is too long')
            return None
        if len(module_name) > 100:
            print(f'Skipping Job model creation from "{class_path}" as the module_name is too long')
            return None
        if len(job_class_name) > 100:
            print(f'Skipping Job model creation from "{class_path}" as the job_class_name is too long')
            return None

        job_model, created = job_model_class.objects.get_or_create(
            source=source,
            module_name=module_name,
            job_class_name=job_class_name,
            # AutoSlugField.slugify_function isn't applied during migrations, need to manually generate slug
            slug=slugify_dots_to_dashes(f"{source}-{module_name}-{job_class_name}")[:320],
            defaults={
                "grouping": module_name,
                "name": job_class_name,
                "installed": False,
                # Since it was previously run or scheduled, let's assume it's enabled for running
                "enabled": True,
            },
        )
        if created:
            print(f'Created Job model "{module_name}: {job_class_name}" for {class_path}')
        return job_model
    except ValueError:
        # class_path doesn't contain the expected number of slashes? Well, we tried!
        return None


def migrate_job_data(apps, schema_editor):
    """
    For all existing JobResults referencing a Job, update them to reference a Job model, creating the model if needed.
    """
    ContentType = apps.get_model("contenttypes", "ContentType")
    Job = apps.get_model("extras", "Job")
    JobResult = apps.get_model("extras", "JobResult")
    ScheduledJob = apps.get_model("extras", "ScheduledJob")

    job_ct = ContentType.objects.get_for_model(Job)

    # Shouldn't be needed but I've seen cases where it happens - not sure exactly why
    for job_jobresult in JobResult.objects.filter(obj_type__model="jobmodel"):
        print("Fixing up content type on {job_jobresult}")
        job_jobresult.obj_type = job_ct
        job_jobresult.save()

    for job_jobresult in JobResult.objects.filter(obj_type=job_ct):
        job_model = _create_job_model(Job, job_jobresult.name)
        if job_model:
            job_jobresult.job_model = job_model
            job_jobresult.save()

    for scheduled_job in ScheduledJob.objects.all():
        job_model = _create_job_model(Job, scheduled_job.job_class)
        if job_model:
            scheduled_job.job_model = job_model
            scheduled_job.save()


def reverse_migrate_job_data(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    JobResult = apps.get_model("extras", "JobResult")
    Job = apps.get_model("extras", "Job")
    ScheduledJob = apps.get_model("extras", "ScheduledJob")

    job_ct = ContentType.objects.get_by_natural_key("extras", "job")

    for job_jobresult in JobResult.objects.filter(obj_type=job_ct):
        job_jobresult.job_model = None
        job_jobresult.save()

    for scheduled_job in ScheduledJob.objects.all():
        scheduled_job.job_model = None
        scheduled_job.save()

    Job.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("extras", "0023_job_model"),
    ]

    operations = [
        migrations.RunPython(migrate_job_data, reverse_migrate_job_data),
    ]
