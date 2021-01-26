# Job Results

NetBox provides a generic data model for storing and reporting the results of background tasks, such as the execution of [custom jobs](../../additional-features/custom-jobs.md) or the synchronization of data from a [Git repository](gitrepository.md).

Records of this type store the following data:

- A reference to the type and name of the object or feature that the task was associated with
- A reference to the user who initiated the task
- Timestamps indicating when the task was created and when it completed
- An overall status such as "pending", "running", "errored", or "completed".
- A block of structured data (often rendered as JSON); by convention this block is used to store detailed log records of the task execution, but it may in theory be used (such as by a plugin) to store other forms of structured data as well.
