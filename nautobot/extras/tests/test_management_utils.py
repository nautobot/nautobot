from unittest.mock import MagicMock, patch

from django.core.management.base import OutputWrapper

from nautobot.core.testing import TestCase
from nautobot.extras.management.utils import handle_eager_result_failure


class TestHandleEagerResultFailure(TestCase):
    """Unit tests for handle_eager_result_failure."""

    def _make_command(self):
        command = MagicMock()
        command.stderr = MagicMock(spec=OutputWrapper)
        return command

    def _make_eager_result(self, failed, result=None, traceback=None):
        eager_result = MagicMock()
        eager_result.result = result
        eager_result.traceback = traceback
        return eager_result

    def test_writes_traceback_to_stderr_when_available(self):
        """Writes the full traceback string to stderr when eager_result.traceback is set."""
        traceback_str = "Traceback (most recent call last):\n  ...\nTypeError: some error\n"
        eager_result = self._make_eager_result(
            failed=True,
            result=TypeError("some error"),
            traceback=traceback_str,
        )
        command = self._make_command()

        with patch("sys.exit") as mock_exit:
            handle_eager_result_failure(command, eager_result)

        command.stderr.write.assert_called_once_with(traceback_str)  # pylint: disable=no-member
        mock_exit.assert_called_once_with(1)

    def test_writes_exc_type_and_message_to_stderr_when_traceback_missing(self):
        """Falls back to writing exc type and message when eager_result.traceback is None."""
        eager_result = self._make_eager_result(
            failed=True,
            result=ValueError("bad value"),
            traceback=None,
        )
        command = self._make_command()

        with patch("sys.exit") as mock_exit:
            handle_eager_result_failure(command, eager_result)

        command.stderr.write.assert_called_once_with("ValueError: bad value\n")  # pylint: disable=no-member
        mock_exit.assert_called_once_with(1)
