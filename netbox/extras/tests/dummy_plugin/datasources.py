from extras.registry import DatasourceContent


def refresh_git_text_files(repository, job_result):
    if "dummy_plugin.TextFile" in repository.provided_contents:
        job_result.log(message="Refreshed text files")


datasource_contents = [
    (
        'extras.GitRepository',
        DatasourceContent(
            name='text files',
            token='dummy_plugin.TextFile',
            icon='mdi-note-text',
            callback=refresh_git_text_files,
        ),
    ),
]
