"""The gate a dispatch path consults before executing an action."""

import logging

from nautobot.extras.conditions.check import check
from nautobot.extras.conditions.payload import build_event_payload

logger = logging.getLogger(__name__)


class ConditionGate:
    """Whether each action's conditions accept the change being dispatched."""

    def __init__(self):
        self._reported = set()

    def accepted(self, actions, object_change, snapshots=None):
        """
        The actions that should run for `object_change`, in the order given.

        Args:
            actions (iterable): Webhooks or job hooks already selected by object type and event.
            object_change (ObjectChange): The change being dispatched.
            snapshots (dict): The before/after data snapshots for `object_change`, when the caller has
                them already. Computed here, with one query, when omitted.

        Returns:
            (list): The actions whose conditions all passed. One whose conditions could not be evaluated
                is left out, and logged.
        """
        # Built only when an action has conditions to read it.
        payload = None
        if any(action.has_conditions for action in actions):
            payload = build_event_payload(object_change, snapshots)
        return [action for action in actions if self._accepts(action, payload)]

    def _accepts(self, action, payload):
        """Whether `action` should run for the change that `payload` describes."""
        if not action.has_conditions:
            return True

        try:
            verdict = check(action.conditions, payload)
        except Exception as error:
            # Only a validated save stores a list of rows; anything else in the column arrives here,
            # and a misconfigured action must not take the save down with it.
            self._report(action, None, f"{type(error).__name__}: {error}")
            return False

        for row in verdict.rows:
            if row.error:
                self._report(action, row.index, row.error)
        return verdict.passed

    def _report(self, action, index, error):
        """Log a condition that could not be evaluated, the first time this gate sees it."""
        if (action.pk, index) in self._reported:
            return

        self._reported.add((action.pk, index))
        logger.error(
            "%s `%s`: %s could not be evaluated, so it does not match: %s",
            action._meta.verbose_name,
            action,
            "its conditions" if index is None else f"condition {index + 1}",
            error,
        )
