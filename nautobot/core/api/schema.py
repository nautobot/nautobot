import re

from drf_spectacular.openapi import AutoSchema


class NautobotAutoSchema(AutoSchema):
    """Nautobot-specific extensions to drf-spectacular's AutoSchema."""

    def get_operation_id(self):
        """Extend the base method to handle Nautobot's REST API bulk operations.

        Without this extension, every one of our ModelViewSet classes will result in drf-spectacular complaining
        about operationId collisions, e.g. between DELETE /api/dcim/devices/ and DELETE /api/dcim/devices/<pk>/ would
        both get resolved to the same "dcim_devices_destroy" operation-id and this would make drf-spectacular complain.

        With this extension, the bulk endpoints automatically get a different operation-id from the non-bulk endpoints.
        """
        if hasattr(self.view, "action") and self.view.action in ["bulk_update", "bulk_partial_update", "bulk_destroy"]:
            # Same basic sequence of calls as AutoSchema.get_operation_id,
            # except we use "self.view.action" instead of "self.method_mapping[self.method]" to get the action verb
            tokenized_path = self._tokenize_path()
            tokenized_path = [t.replace("-", "_") for t in tokenized_path]

            action = self.view.action

            if not tokenized_path:
                tokenized_path.append("root")
            if re.search(r"<drf_format_suffix\w*:\w+>", self.path_regex):
                tokenized_path.append("formatted")

            return "_".join(tokenized_path + [action])

        # For all other view actions, operation-id is the same as in the base class
        return super().get_operation_id()
