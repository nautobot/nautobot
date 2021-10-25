from collections import OrderedDict
from django.db import migrations

from nautobot.extras.choices import LogLevelChoices


"""
This is the loose structure that we are trying to extract logs from (or restore to in case of reverse):

data = {
    "main": {
        "log": [
            [timestamp, log_level, object_name, object_url, message],
            [timestamp, log_level, object_name, object_url, message],
            [timestamp, log_level, object_name, object_url, message],
            ...
        ],
        "success": <count of log messages with log_level "success">,
        "info": <count of log messages with log_level "info">,
        "warning": <count of log messages with log_level "warning">,
        "failure": <count of log messages with log_level "failure">,
    },
    "grouping1": {
        "log": [...],
        "success": <count>,
        "info": <count>,
        "warning": <count>,
        "failure": <count>,
    },
    "grouping2": {...},
    ...
    "total": {
        "success": <total across main and all other groupings>,
        "info": <total across main and all other groupings>,
        "warning": <total across main and all other groupings>,
        "failure": <total across main and all other groupings>,
    },
    "output": <optional string, such as captured stdout/stderr>,
}
"""


def _data_grouping_struct():
    return OrderedDict(
        [
            ("success", 0),
            ("info", 0),
            ("warning", 0),
            ("failure", 0),
            ("log", []),
        ]
    )


def migrate_params(apps, schema_editor):
    JobResult = apps.get_model("extras", "JobResult")
    JobLogEntry = apps.get_model("extras", "JobLogEntry")

    for job_result in JobResult.objects.all():
        if job_result.data:
            keys_to_remove = []
            for key, value in job_result.data.items():
                # Ensure we process only the groupings
                if isinstance(value, dict) and value.get("log") and value.get("success"):
                    keys_to_remove.append(key)
                    for log in value["log"]:
                        entry = JobLogEntry(
                            grouping=key,
                            job_result=job_result,
                            created=log[0],
                            log_level=log[1],
                            log_object=log[2],
                            absolute_url=log[3],
                            message=log[4],
                        )
                        entry.save()
                if key == "total":
                    keys_to_remove.append(key)

            for item in keys_to_remove:
                job_result.data.pop(item)
        job_result.save()


def reverse_migrate_params(apps, schema_editor):
    JobResult = apps.get_model("extras", "JobResult")
    JobLogEntry = apps.get_model("extras", "JobLogEntry")

    for entry in JobLogEntry.objects.all():
        job_result = JobResult.objects.get(pk=entry.job_result.pk)
        if not job_result.data:
            job_result.data = {}

        job_result.data.setdefault(entry.grouping, _data_grouping_struct())

        if "log" not in job_result.data[entry.grouping]:
            job_result.data[entry.grouping]["log"] = []
        log = job_result.data[entry.grouping]["log"]

        log.append(
            [
                entry.created,
                entry.log_level,
                entry.log_object,
                entry.absolute_url or None,
                entry.message,
            ]
        )

        if entry.log_level != LogLevelChoices.LOG_DEFAULT:
            job_result.data[entry.grouping].setdefault(entry.log_level, 0)
            job_result.data[entry.grouping][entry.log_level] += 1
            if "total" not in job_result.data:
                job_result.data["total"] = _data_grouping_struct()
                del job_result.data["total"]["log"]
            job_result.data["total"].setdefault(entry.log_level, 0)
            job_result.data["total"][entry.log_level] += 1

        job_result.save()


class Migration(migrations.Migration):

    dependencies = [
        ("extras", "0016_joblogentry"),
    ]

    operations = [
        migrations.RunPython(migrate_params, reverse_migrate_params),
    ]


data = {
    "main": {
        "log": [
            ["timestamp1", "log_level1", "object_name1", "object_url1", "message1"],
            ["timestamp2", "log_level2", "object_name2", "object_url2", "message2"],
            ["timestamp3", "log_level3", "object_name3", "object_url3", "message3"],
        ],
        "success": 2,
        "info": 1,
        "warning": 0,
        "failure": 0,
    },
    "grouping1": {
        "log": [
            ["timestamp1", "log_level1", "object_name1", "object_url1", "message1"],
            ["timestamp2", "log_level2", "object_name2", "object_url2", "message2"],
        ],
        "success": 1,
        "info": 0,
        "warning": 1,
        "failure": 0,
    },
    "grouping2": {
        "log": [
            ["timestamp1", "log_level1", "object_name1", "object_url1", "message1"],
        ],
        "success": 0,
        "info": 0,
        "warning": 0,
        "failure": 1,
    },
    "total": {
        "success": 3,
        "info": 1,
        "warning": 1,
        "failure": 1,
    },
    "output": "This should stay",
}
