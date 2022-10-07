# Job Results

Nautobot provides a generic data model for storing and reporting the results of background tasks, such as the execution of custom jobs or the synchronization of data from a Git repository.

Records of this type store the following data:

- A reference to the type and name of the object or feature that the task was associated with
- A reference to the user who initiated the task
- The arguments that were passed to the task (allowing for later queuing of the task for re-execution if desired)
- Timestamps indicating when the task was created and when it completed
- An overall status such as "pending", "running", "errored", or "completed".
- A block of structured data (often rendered as JSON); Any return values from the `.run()` and any `test` methods go to the key `output`. In addition any Job or plugin using the `JobResult` model can store arbitrary structured data here if needed. (Note that prior to Nautobot 1.2, job log records were stored in this field; they are now stored as distinct [`JobLogEntry`](joblogentry.md) records instead.)
