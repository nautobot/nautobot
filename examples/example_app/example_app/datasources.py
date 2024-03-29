from nautobot.apps.datasources import DatasourceContent


def refresh_git_text_files(repository, job_result, delete=False):
    if "example_app.textfile" in repository.provided_contents:
        job_result.log(message="Refreshed text files")


datasource_contents = [
    (
        "extras.gitrepository",
        DatasourceContent(
            name="text files",
            content_identifier="example_app.textfile",
            icon="mdi-note-text",
            callback=refresh_git_text_files,
        ),
    ),
]
