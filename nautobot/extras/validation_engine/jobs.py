from nautobot.extras.jobs import Job
from nautobot.extras.utils import registry

class RunRegisteredValidations(Job):
    def run(self, data, commit):
        for model, classes in registry["plugin_validations"].items():
            for validation_class in classes:
                ins = validation_class()
                self.log_info(f"Running {ins.name}")
                ins.validate()

jobs = [RunRegisteredValidations]