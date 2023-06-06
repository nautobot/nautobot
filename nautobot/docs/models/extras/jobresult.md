# Job Results

Nautobot provides a generic data model for storing and reporting the results of background tasks, such as the execution of custom jobs or the synchronization of data from a Git repository.

Records of this type store the following data:

- A reference to the job model that the task was associated with
- A reference to the user who initiated the task
- If initiated by a scheduled job, a reference to that scheduled job instance
- The arguments that were passed to the task (allowing for later queuing of the task for re-execution if desired)
- Timestamps indicating when the task was created and when it completed
- An overall status such as "pending", "running", "errored", or "completed".
- A block of structured data representing the return value from the `.run()` method (often rendered as JSON).

+/- 1.2.0
    Note that prior to Nautobot 1.2, job log records were stored in the `data` field; they are now stored as distinct [`JobLogEntry`](joblogentry.md) records instead.
