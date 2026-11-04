# App Code Updates for Nautobot v3

## Deprecated Templates

Over time, some templates have been deprecated and either consolidated or replaced with new ones.
If you are using a deprecated template, you should migrate to the new template.
We have included a script to help migrate all html files that extend a deprecated template to the new template.
You can run it with the following command:

```bash
nautobot-migrate-deprecated-templates <path-to-your-app> [--dry-run]
```

This will recursively find all `.html` files in the given path and replace extends references (`{% extends 'path/to/deprecated_template.html' %}`) to deprecated templates with the replacement ones.
You can also run it with the `--dry-run` flag to see what changes would be made without actually making any changes.

For a list of deprecated templates and their replacements, see the following table:

??? info "Full table of deprecated templates and their replacements"
    {data-table development/apps/migration/tables/deprecated-html-templates.yml}
