"""Utilities for an app to register datasource contents (for Git, etc.)."""

from nautobot.extras.datasources.git import (
    delete_git_config_context_schemas,
    delete_git_config_contexts,
    delete_git_export_templates,
    enqueue_git_repository_diff_origin_and_local,
    enqueue_git_repository_helper,
    enqueue_pull_git_repository_and_refresh_data,
    ensure_git_repository,
    get_repo_from_url_to_path_and_from_branch,
    git_repository_dry_run,
    import_config_context,
    import_config_context_schema,
    import_local_config_context,
    refresh_code_from_repository,
    refresh_git_config_context_schemas,
    refresh_git_config_contexts,
    refresh_git_export_templates,
    refresh_git_jobs,
    update_git_config_context_schemas,
    update_git_config_contexts,
    update_git_export_templates,
)
from nautobot.extras.datasources.registry import (
    get_datasource_content_choices,
    get_datasource_contents,
    refresh_datasource_content,
)
from nautobot.extras.datasources.utils import files_from_contenttype_directories
from nautobot.extras.registry import DatasourceContent


__all__ = (
    "DatasourceContent",
    "delete_git_config_context_schemas",
    "delete_git_config_contexts",
    "delete_git_export_templates",
    "enqueue_git_repository_diff_origin_and_local",
    "enqueue_git_repository_helper",
    "enqueue_pull_git_repository_and_refresh_data",
    "ensure_git_repository",
    "files_from_contenttype_directories",
    "get_datasource_content_choices",
    "get_datasource_contents",
    "get_repo_from_url_to_path_and_from_branch",
    "git_repository_dry_run",
    "import_config_context_schema",
    "import_config_context",
    "import_local_config_context",
    "refresh_code_from_repository",
    "refresh_datasource_content",
    "refresh_git_config_context_schemas",
    "refresh_git_config_contexts",
    "refresh_git_export_templates",
    "refresh_git_jobs",
    "update_git_config_context_schemas",
    "update_git_config_contexts",
    "update_git_export_templates",
)
