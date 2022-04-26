from django.db import migrations


def migrate_job_data(apps, schema_editor):
    """
    For all existing Job models referencing a GitRepository by slug, update them to foreign key references.
    """
    Job = apps.get_model("extras", "Job")
    GitRepository = apps.get_model("extras", "GitRepository")

    for job in Job.objects.filter(source__startswith="git."):
        repo_slug = job.source[4:]
        try:
            repo = GitRepository.objects.get(slug=repo_slug)
            job.git_repository = repo
        except GitRepository.DoesNotExist:
            print(f'Git repository "{repo_slug}" not found for Job {job.module_name} {job.job_class_name}!')
        job.source = "git"
        job.save()


def reverse_migrate_job_data(apps, schema_editor):
    Job = apps.get_model("extras", "Job")

    for job in Job.objects.filter(source="git"):
        if job.git_repository is not None:
            job.source = f"git.{job.git_repository.slug}"
        else:
            print(f"Job {job.module_name} {job.job_class_name} s has no Git repository")
            job.source = "git.unknown-repository"
        job.save()


class Migration(migrations.Migration):

    dependencies = [
        ("extras", "0026_job_add_gitrepository_fk"),
    ]

    operations = [
        migrations.RunPython(migrate_job_data, reverse_migrate_job_data),
    ]
