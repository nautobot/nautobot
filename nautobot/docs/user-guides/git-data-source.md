# Git as a Data Source

The Nautobot Git as a Data Source feature was developed to provide the ability to populate existing data, templates, scripts, and much more into Nautobot.  While using the benefits that Github already provides with issue tracking, discussions, pipelines, and approvals.

For more in depth details on how this feature [see](https://nautobot.readthedocs.io/en/latest/models/extras/gitrepository/).


## Supported Providers
The feature uses the concept of a `provides` field to map a repository to a use case. A list of the supported options is provided below.

|Name|Summary|Related Plugin|
|:--|:--:|--:|
|Export Templates|Nautobot allows users to define custom templates that can be used when exporting objects.|N/A|
|Jobs|Jobs are a way for users to execute custom logic on demand from within the Nautobot UI. Jobs can interact directly with Nautobot data to accomplish various data creation, modification, and validation tasks.|N/A|
|Config Contexts||[Golden Config](https://github.com/nautobot/nautobot-plugin-golden-config)|
|Backup Configs|Backup configuration data.|[Golden Config](https://github.com/nautobot/nautobot-plugin-golden-config)|
|Intended Configs|Stores the intended configurations, this grabs Nautobot data and runs through Jinja Templates.|[Golden Config](https://github.com/nautobot/nautobot-plugin-golden-config)|
|Jinja Templates|Repository that holds Jinja templates to be used to generate intended configs.|[Golden Config](https://github.com/nautobot/nautobot-plugin-golden-config)|

## Repository Details

Parameters:
|Field|Explanation|
|:--|:--|
|Name|User friendly name for the repo.|
|Slug|Auto-generated based on the `name` provided.|
|Remote URL|The URL pointing to the Git repo. Current git url usage is limited to `http` or `https`.|
|Branch|The branch in the Git repo to use. Defaults to `main`.|
|Token|The token is a personal access token for the `username` provided.  For more information on generating a personal access token. [Github Personal Access Token](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token)
|Username|The Git username that corresponds with the personal access token above.|
|Provides|Valid providers for Git Repo.|
<br>

## Using Git Data Sources
This section will focus on examples and use the `user-guide` branch on the demo-git-datasources repo: `https://github.com/nautobot/demo-git-datasource`.

### Export Templates
Export Templates allow a user to export Nautobot objects based on a custom template.  Export templates can change over time depending on the needs of a user.  Allowing export templates to reference a git repo makes managing templates easier.

A template can be used to put objects into a specific format for ingestion into another system, tool, or report.  It is possible that different templates are needed depending on specific users or teams.  This can lead to sprawl of export templates.  To keep accurate templates synced with Nautobot the Git Data Sources extensibility feature can be used.

#### Step 1
Navigate to the Data Sources Git integration. `Extensibility -> Git Repositories`.

![](./images/git-data-source_1.png)

Click [+] or [Add]

That loads a default page to add a repository.

![](./images/git-data-source_2.png)

> By default only config contexts, export templates, and jobs are implemented.  Other data sources will get added when a specific plugin is used.

#### Step 2
Fill out the details for the Git repository. See [fields](#repository-details).

![](./images/git-data-source_3.png)

As soon as you click on `Create`, Nautobot will clone and sync the repository and provide status of the job.

![](./images/git-data-source_4.png)
![](./images/git-data-source_6.png)

The repository will now be displayed on the main Git Repository page.

![](./images/git-data-source_5.png)

Once the repository is synced each template will now be available in the Export Templates section.  `Extensibility -> Export Templates`.

![](./images/git-data-source_7.png)

>Note: If the templates don't populate make sure your git directory is named `export-templates` with the Nautobot `content type` for the object as folders.  Example below:

```bash
▶ tree export_templates 
export_templates
└── dcim
    └── device
        ├── markdown_export.md
        ├── text_export.txt
        └── yaml_export.yml

2 directories, 3 files
```

#### Step 3
Now that the export templates have been loaded into Nautobot they can be utilized as normal.  For example navigate to `Devices -> Devices` and click on `Export` in the top right corner, the dropdown will now include the templates loaded from the Git repository.

The power of having export templates utilizing the git integration comes with the native source control features that git comes with.  To illusturate a simple git sync within Nautobot assume the following template needs to be updated.

Filename: `/export_templates/dcim/device/yaml_export.yml
Current contents:
```jinja
---
{% for device in queryset %}
{% if device.status %}
- {{ device.name }}:
{% endif %}
{% endfor %}
...
```

The template needs to be modified to provide more information than just a list of hostnames.  The site needs to be added.

The updated template is now:
```jinja
---
{% for device in queryset %}
{% if device.status %}
- {{ device.name }}:
  site: {{ device.site }}
{% endif %}
{% endfor %}
...
```

Once the contributor updates the git repo via normal git processes and it is reviewed and merged into the branch that was used, a sync process from Nautobot needs to be completed.  This can be done from the default git view, or within a specific detailed view of a git repository.

From the default git repositories view:
![](./images/git-data-source_8.png)

From the detailed view:
![](./images/git-data-source_9.png)

> Once the repository has been synced its easy to check the history for the templates.
Navigate to `Git Repositories` and select the repository in question.  Once you're in the detailed view you can look through the `Synchronization Status` or `Change Log` tabs.

Now that the git repository is linked for export templates it can be controlled via the normal git operations workflow, which allows users or groups of users to perform code reviews using Pull Requests etc.

### Jobs
Jobs are a way for users to execute custom logic on demand from within the Nautobot UI. Jobs can interact directly with Nautobot data to accomplish various data creation, modification, and validation tasks.


## Additional Git Data Sources

As seen in [above](#Step-2), the standard installation of Nautobot will come natively with export templates, jobs, and config contexts.  Additional data sources can be incorportated using the Nautobot plugin system.  For example, the [nautobot-plugin-golden-config](https://github.com/nautobot/nautobot-plugin-golden-config) plugin implements four additional data sources.

- Config Contexts
- Backup Configs
- Intended Configs
- Jinja Templates

For more information for the Golden Configuration specific data sources [see](https://github.com/nautobot/nautobot-plugin-golden-config/blob/develop/docs/navigating-golden.md#git-settings).
