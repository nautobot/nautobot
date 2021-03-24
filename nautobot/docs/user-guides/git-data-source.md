# Git as a Data Source

Using Git as a Data Source feature was developed to provide the ability to populate existing data, templates, scripts, and much more into Nautobot; while leveraging the benefits that GitHub already provides including issue tracking, discussions, pipelines, and approvals.

For more technical details on how to use this feature, please see the documentation on [Git Repositories](https://nautobot.readthedocs.io/en/latest/models/extras/gitrepository/).


## Supported Providers
The feature uses the concept of a `provides` field to map a repository to a use case. A list of the supported options is provided below.

|Name|Summary|Related Plugin|
|:--|:--|:--|
|Export Templates|Nautobot allows users to define custom templates that can be used when exporting objects.|Core Functionality|
|Jobs|Jobs are a way for users to execute custom logic on demand from within the Nautobot UI. Jobs can interact directly with Nautobot data to accomplish various data creation, modification, and validation tasks.|Core Functionality|
|Config Contexts|Config contexts can be used to provide additional data that you can't natively store in Nautobot.|Core Functionality|
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
|Token|The token is a personal access token for the `username` provided.  For more information on generating a personal access token. [GitHub Personal Access Token](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token)
|Username|The Git username that corresponds with the personal access token above.|
|Provides|Valid providers for Git Repo.|
<br>

## Using Git Data Sources
This section will focus on examples and use the `user-guide` branch on the demo-git-datasources repo: `https://github.com/nautobot/demo-git-datasource`.

### Export Templates

Export Templates allow a user to export Nautobot objects based on a custom template.  Export templates can change over time depending on the needs of a user.  Allowing export templates to reference a Git repo makes managing templates easier.

A template can be used to put objects into a specific format for ingestion into another system, tool, or report.  It is possible that different templates are needed depending on specific users or teams.  This can lead to sprawl of export templates.  To keep accurate templates synced with Nautobot the Git Data Sources extensibility feature can be used.

#### Step 1
Navigate to the Data Sources Git integration. **Extensibility -> Git Repositories**.

![](./images/git-data-source_1.png)

Click [+] or [Add]

That loads a default page to add a repository.

![](./images/git-data-source_2.png)

> By default only config contexts, export templates, and jobs are implemented.  Other data sources will get added when a specific plugin is used.

#### Step 2
Fill out the details for the Git repository. More information on the inputs can be found in the [fields section](#repository-details).

![](./images/git-data-source_3.png)

As soon as you click on **Create**, Nautobot will clone and sync the repository and provide status of the job.

![](./images/git-data-source_4.png)
![](./images/git-data-source_6.png)

The repository will now be displayed on the main Git Repository page.

![](./images/git-data-source_5.png)

Once the repository is synced each template will now be available in the Export Templates section.  **Extensibility -> Export Templates**.

![](./images/git-data-source_7.png)

> Note: If the templates don't populate make sure the Git directory is named `export-templates` and the Nautobot `content type` for the object is the sub-directory name.

Example below:
```
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
Now that the export templates have been loaded into Nautobot they can be utilized as normal.  For example navigate to **Devices -> Devices** and click on **Export** in the top right corner, the dropdown will now include the templates loaded from the Git repository.

The power of having export templates utilizing the Git integration comes with the native source control features that Git comes with.  To illustrate a simple Git sync within Nautobot assume the following template needs to be updated.

Filename: `/export_templates/dcim/device/yaml_export.yml`

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

Once the contributor updates the Git repository via normal Git processes and it is reviewed and merged into the branch that was used, a sync process from Nautobot needs to be completed.  This can be done from the default Git view, or within a specific detailed view of a Git repository.

From the default Git repositories view:
![](./images/git-data-source_8.png)

From the detailed view:
![](./images/git-data-source_9.png)

> Once the repository has been synced its easy to check the history for the templates.
Navigate to **Git Repositories** and select the repository in question.  Once you're in the detailed view you can look through the **Synchronization Status** or **Change Log** tabs.

Now that the Git repository is linked for export templates it can be controlled via the normal Git operations workflow, which allows users or groups of users to perform code reviews using Pull Requests etc.

### Jobs
Jobs are a way for users to execute custom logic on demand from within the Nautobot UI. Jobs can interact directly with Nautobot data to accomplish various data creation, modification, and validation tasks.

For technical details on jobs, please see the documentation on [jobs](https://nautobot.readthedocs.io/en/latest/additional-features/jobs/#jobs).

Jobs allow a user to write scripts in Python.  By integrating the scripts with Git, a user can utilize Git workflows to manage source control, versioning, and pipelines.

Setting up the repository can be done following the same steps from [Export Templates](#Export-Templates).  The only differences is the `provides` selection changes to `jobs`.

Jobs need to be defined in `/jobs/` directory at the root of a Git repository.

An example tree for `/jobs/`.

```
▶ tree jobs 
jobs
├── __init__.py
└── get-device-connection.py

1 directory, 2 files
```

Once the repository is created in Nautobot.
![](./images/git-data-source_10.png)

> Note: The same repository and branch can be used for the different `provides` methods.  Nautobot Git as a data source will look for specific root directory names.

Once the scripts have been pushed into the repository, a sync needs to be executed, after which navigating to Jobs via **Extensibility -> Jobs** will show the new jobs loaded from the Git repository.

![](./images/git-data-source_11.png)

Jobs now shows the job from the Git repository.

![](./images/git-data-source_12.png)

At this point all changes, and history can be kept using Git.  A simple `sync` operation can be done from Nautobot to pulldown any changes.

### Config Contexts
Detailed information on [config contexts](https://nautobot.readthedocs.io/en/latest/models/extras/gitrepository/#configuration-contexts).

Config contexts may be provided as JSON or YAML files located in `/config_contexts/`.

Config contexts can be used to provide additional details to different automation tooling.  For example `Ansible vars`, or any other data that you can't natively store in Nautobot.  It can also be used in the Golden Configuration Nautobot plugin to provide extra details to generate configuration templates.

A few simple examples of Configuration Context data might be:
 - DNS Servers
 - NTP Servers
 - ACL Data
 - Routing Information such as BGP ASNs etc.

Similar to the other data sources, the repository can be added by navigating to **Extensibility -> Git repositories**. Click on **Add**, and fill out the repository details.

![](./images/git-data-source_13.png)

Once the repository syncs the details can be found in the **Synchronization Status** tab.  For example the platform specifics were synced.

![](./images/git-data-source_14.png)

The repository structure is:
```
▶ tree config_contexts 
config_contexts
├── devices
│   ├── site-a-bb-01.yml
│   ├── site-a-rtr-01.yml
│   ├── site-a-rtr-02.yml
│   ├── site-a-spine-01.yml
│   ├── site-a-spine-02.yml
│   ├── site-b-bb-01.yml
│   ├── site-b-leaf-01.yml
│   ├── site-b-leaf-02.yml
│   ├── site-b-rtr-01.yml
│   ├── site-b-rtr-02.yml
│   ├── site-b-spine-01.yml
│   └── site-b-spine-02.yml
├── platform_eos.yml
├── platform_junos.yml
├── platform_nxos.yml
└── role_spine.yml

1 directory, 16 files
```

Configuration Context details:
- Follows an inheritance methodology similar to what Ansible implements.  Global contexts can be overwritten by local contexts at both a group level, as well as at a device specific level.
- Nautobot UI provides a simple view to see merged config contexts.  It can be visualized by navigating to a device and clicking on the **config contexts** tab.

Here's an example, with some of the details omitted for brevity.

![](./images/git-data-source_15.png)

There is a huge benefit to having `config contexts` managed by a Git workflow.  This type of data can be modified often, especially platform specifics, or new device roles.  Utilizing a standard Git workflow allows for all the proper reviews and approvals to be accomplished before accepting the changes into Nautobot for use.


## Additional Git Data Sources

As seen in [Step 2](#Step-2), the standard installation of Nautobot will come natively with export templates, jobs, and config contexts.  Additional data sources can be incorporated using the Nautobot plugin system.  For example, the [nautobot-plugin-golden-config](https://github.com/nautobot/nautobot-plugin-golden-config) plugin implements four additional data sources.

- Config Contexts
- Backup Configs
- Intended Configs
- Jinja Templates

For more information for the Golden Configuration specific data sources, navigate to [Nautobot Golden Config Repo](https://github.com/nautobot/nautobot-plugin-golden-config/blob/develop/docs/navigating-golden.md#git-settings).
