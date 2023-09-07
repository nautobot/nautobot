# User Preferences

The `users.User` model holds individual preferences for each user in the form of JSON data in the `config_data` field. This page serves as a manifest of all recognized user preferences in Nautobot.

## Available Preferences

| Name | Description |
| ---- | ----------- |
| `extras.configcontext.format` | Preferred format when rendering config context data (JSON or YAML) |
| `pagination.per_page` | The number of items to display per page of a paginated table |
| `tables.TABLE_NAME.columns` | The ordered list of columns to display when viewing the table |
