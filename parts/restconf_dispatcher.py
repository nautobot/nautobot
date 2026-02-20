import json
import os

import requests
from netutils.config.clean import clean_config, sanitize_config
from nornir.core.exceptions import NornirSubTaskError
from nornir.core.task import Result, Task
from nornir_nautobot.exceptions import NornirNautobotException
from nornir_nautobot.plugins.tasks.dispatcher.default import DispatcherMixin
from nornir_nautobot.utils.helpers import make_folder
from requests.auth import HTTPBasicAuth


# curl -X GET https://10.100.1.217:80/restconf/data/system/config --header 'Accept: application/yang-data+json' -u admin:cisco  --insecure
# curl -X GET https://10.100.1.217:80/restconf/data/netconf-state/capabilities --header 'Accept: application/yang-data+json' -u admin:cisco  --insecure
# curl -X GET https://10.100.1.217:80/restconf/data/yang-library --header 'Accept: application/yang-data+json' -u admin:cisco  --insecure


def restconf_get_config(
    task: Task,
) -> Result:
    """Get the latest configuration from the device using restconf."""
    requests.packages.urllib3.disable_warnings()
    headers = {"Content-Type": "application/yang-data+json", "Accept": "application/yang-data+json"}
    api_call = f"https://{task.host.hostname}:80/restconf/data/ietf-system:system"
    # api_call = f"https://{task.host.hostname}:80/restconf/data/openconfig-system:system"
    print(task.host.username, task.host.password)
    result = requests.get(
        api_call, auth=HTTPBasicAuth(task.host.username, task.host.password), headers=headers, verify=False
    )
    print(result.text)
    return Result(host=task.host, result=result.json())


class RestconfDefault(DispatcherMixin):
    """Custom dispatcher to add Restconf support to GC."""

    @classmethod
    def get_config(  # pylint: disable=R0913,R0914
        cls, task: Task, logger, obj, backup_file: str, remove_lines: list, substitute_lines: list
    ) -> Result:
        """Get the latest configuration from the device using restconf. Overrides default get_config.

        This use Reuest library to get the configuration from the device.

        Args:
            task (Task): Nornir Task.
            logger (logging.Logger): Logger that may be a Nautobot Jobs or Python logger.
            obj (Device): A Nautobot Device Django ORM object instance.
            remove_lines (list): A list of regex lines to remove configurations.
            substitute_lines (list): A list of dictionaries with to remove and replace lines.

        Returns:
            Result: Nornir Result object with a dict as a result containing the running configuration
                { "config: <running configuration> }
        """
        logger.debug(f"Executing get_config for {task.host.name} on {task.host.platform}")
        try:
            result = task.run(
                task=restconf_get_config,
            )
        except NornirSubTaskError as exc:
            error_msg = f"`E1015:` `get_config` method failed with an unexpected issue: `{exc.result.exception}`"
            logger.error(error_msg, extra={"object": obj})
            raise NornirNautobotException(error_msg)

        if result[0].failed:
            return result

        running_config = result[0].result

        if remove_lines:
            logger.debug("Removing lines from configuration based on `remove_lines` definition")
            running_config = clean_config(running_config, remove_lines)
        if substitute_lines:
            logger.debug("Substitute lines from configuration based on `substitute_lines` definition")
            running_config = sanitize_config(running_config, substitute_lines)

        if backup_file:
            make_folder(os.path.dirname(backup_file))

            with open(backup_file, "w", encoding="utf8") as filehandler:
                filehandler.write(json.dumps(running_config, indent=4))
        return Result(host=task.host, result={"config": running_config})
