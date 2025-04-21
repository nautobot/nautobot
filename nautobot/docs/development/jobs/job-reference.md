
### Reserved Attribute Names
<!-- move:job-reference.md -->
There are many attributes and methods of the Job class that serve as reserved names. You must be careful when implementing custom methods or defining the user input [variables](#variables) for your Job that you do not inadvertently "step on" one of these reserved attributes causing unexpected behavior or errors.

!!! example
    One classic pitfall here is the the reserved `name` metadata attribute - if you attempt to redefine `name` as a user input variable, your Job will not work.

As of Nautobot 2.4.0, the current list of reserved names (not including low-level Python built-ins such as `__dict__` or `__str__` includes:

| Reserved Name             | Purpose                                                 |
| ------------------------- | ------------------------------------------------------- |
| `after_return`            | [special method](#special-methods)                      |
| `approval_required`       | [metadata property](#approval_required)                 |
| `as_form`                 | class method                                            |
| `as_form_class`           | class method                                            |
| `before_start`            | [special method](#special-methods)                      |
| `celery_kwargs`           | property                                                |
| `class_path`              | class property                                          |
| `class_path_dotted`       | deprecated class property                               |
| `class_path_js_escaped`   | class property                                          |
| `create_file`             | [helper method](#file-output)                           |
| `description`             | [metadata property](#description)                       |
| `description_first_line`  | [metadata property](#description)                       |
| `deserialize_data`        | internal class method                                   |
| `dryrun_default`          | [metadata property](#dryrun_default)                    |
| `fail`                    | [helper method](#marking-a-job-as-failed)               |
| `file_path`               | deprecated class property                               |
| `field_order`             | [metadata property](#field_order)                       |
| `grouping`                | [module metadata property](#module-metadata-attributes) |
| `has_sensitive_variables` | [metadata property](#has_sensitive_variables)           |
| `hidden`                  | [metadata property](#hidden)                            |
| `is_singleton`            | [metadata property](#is_singleton)                      |
| `job_model`               | property                                                |
| `job_result`              | property                                                |
| `load_json`               | [helper method](#reading-data-from-files)               |
| `load_yaml`               | [helper method](#reading-data-from-files)               |
| `name`                    | [metadata property](#name)                              |
| `on_failure`              | [special method](#special-methods)                      |
| `on_retry`                | reserved as a future [special method](#special-methods) |
| `on_success`              | [special method](#special-methods)                      |
| `prepare_job_kwargs`      | internal class method                                   |
| `properties_dict`         | class property                                          |
| `read_only`               | [metadata property](#read_only)                         |
| `registered_name`         | deprecated class property                               |
| `run`                     | [special method](#special-methods)                      |
| `serialize_data`          | internal method                                         |
| `soft_time_limit`         | [metadata property](#soft_time_limit)                   |
| `supports_dryrun`         | class property                                          |
| `task_queues`             | [metadata property](#task_queues)                       |
| `template_name`           | [metadata property](#template_name)                     |
| `time_limit`              | [metadata property](#time_limit)                        |
| `user`                    | property                                                |
| `validate_data`           | internal class method                                   |
