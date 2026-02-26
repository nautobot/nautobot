import functools
import logging
from queue import Empty, Queue
import subprocess
import sys
import threading
from typing import Any, Dict

from django.utils import timezone

from nautobot.extras.choices import JobConsoleEntryOutputTypeChoices
from nautobot.extras.models import JobConsoleEntry, JobResult

logger = logging.getLogger(__name__)


class JobConsoleLogSubprocessError(subprocess.SubprocessError):
    """Raised when a job console log subprocess fails."""

    def __init__(self, message=None, returncode=None, stderr=None):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


def store_job_output_line(job_result: JobResult, data: str, output_type: str = "output", timestamp=None):
    """
    Store output from a job console log execution as a new line in the database.

    Args:
        job_result (JobResult): JobResult instance to associate the line to
        data (str): Line of output data
        output_type (str): Type of output ('stdout' or 'stderr')
        timestamp (datetime): Optional timestamp (defaults to now)
    """

    if timestamp is None:
        timestamp = timezone.now()

    if not data:
        return

    JobConsoleEntry.objects.create(job_result=job_result, timestamp=timestamp, output_type=output_type, text=data)


#
# StreamReader
#


class StreamReader:
    """
    Reads from a process stream and stores output to database.
    """

    def __init__(self, output_type: str, store_func: callable):
        """
        Initialize stream reader.

        Args:
            output_type (str): 'stdout' or 'stderr'
            store_func (callable): Function to call to store each line
        """
        self.output_type = output_type
        self.store_func = store_func
        self.queue = Queue()  # not sure that it's still needed if you use database now.
        self.thread = None

    def read_and_store(self, stream):
        """Read from stream, store in DB, and queue."""
        try:
            for line in iter(stream.readline, ""):
                self.store_func(data=line)
                self.queue.put(line)

        except Exception as e:
            logger.error(f"Error reading {self.output_type}: {e}")
        finally:
            stream.close()
            self.queue.put(None)  # Signal end of stream

    def start_thread(self, stream):
        """Start reading stream in background thread."""
        self.thread = threading.Thread(target=self.read_and_store, args=(stream,))
        self.thread.start()
        return self

    def join(self):
        """Wait for reader thread to finish."""
        if self.thread:
            self.thread.join()

    def drain_queue(self):
        """Generator that yields lines from queue until stream ends."""
        while True:
            try:
                line = self.queue.get(timeout=0.01)
                if line is None:  # End of stream
                    break
                yield line
            except Empty:
                continue


#
# JobConsoleLogExecutor
#


class JobConsoleLogExecutor:
    """
    Main class for executing console log jobs and capturing output.
    """

    def __init__(self, job_result_pk: str, print_output: bool = False):
        """
        Initialize job executor.

        Args:
            job_result_pk (str): Primary key of JobResult
            print_output (bool): Whether to enable real-time console output
        """

        self.job_result_pk = job_result_pk
        self.job_result = JobResult.objects.get(pk=job_result_pk)
        self.print_output = print_output

        store_stdout = functools.partial(store_job_output_line, job_result=self.job_result, output_type="stdout")
        store_stderr = functools.partial(store_job_output_line, job_result=self.job_result, output_type="stderr")

        self.stdout_reader = StreamReader("stdout", store_stdout)
        self.stderr_reader = StreamReader("stderr", store_stderr)

        self.process = None
        self.return_code = None

    def _build_command(self) -> list:
        """Build command to execute."""
        return [f"{sys.argv[0]}", "execute_job_result", f"{self.job_result_pk}", "--console_log"]

    def _print_output(self):
        """Print output in real-time while process runs."""
        print(" === STDOUT ===")
        for line in self.stdout_reader.drain_queue():
            print(line, end="")
        print(" === END STDOUT ===")

        print(" === STDERR ===")
        for line in self.stderr_reader.drain_queue():
            print(line, end="")
        print(" === END STDERR ===")

    def _handle_failure(self):
        """Handle job failure by raising exception with stderr."""
        if self.return_code != 0:
            stderr_lines = JobConsoleEntry.objects.filter(
                job_result=self.job_result, output_type=JobConsoleEntryOutputTypeChoices.TYPE_STDERR
            ).values_list("text", flat=True)

            stderr = "\n".join(line.rstrip() for line in stderr_lines)
            message = list(stderr_lines)[-1].rstrip() if stderr_lines else None

            raise JobConsoleLogSubprocessError(
                message=message or "Job console log subprocess failed",
                returncode=self.return_code,
                stderr=stderr,
            )

    def execute(self) -> Dict[str, Any]:
        """
        Execute the console log job and capture output.

        Returns:
            Dict with execution results

        Raises:
            Exception: If job execution fails
        """
        cmd = self._build_command()
        with subprocess.Popen(  # noqa: S603 cmd built from trusted internal values
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1,
        ) as process:
            # start stream_readers
            self.stdout_reader.start_thread(process.stdout)
            self.stderr_reader.start_thread(process.stderr)

            if self.print_output:
                self._print_output()

            # waiting for completion
            self.return_code = process.wait()
            self.stdout_reader.join()
            self.stderr_reader.join()

            self._handle_failure()
