# Job Log Entry

+++ 1.2.0

Log messages from [Jobs](../../additional-features/jobs.md) are stored in as `JobLogEntry` objects. This allows more performant querying of log messages and even allows viewing of logs while the job is still running.

Records of this type store the following data:

- A reference to the `JobResult` object that created the log.
- Timestamps indicating when the log message was created.
- The logging level of the log message.
- The log message.
- If provided, the string format of the logged object and it's absolute url.

+++ 1.2.2
    REST API and GraphQL support for querying `JobLogEntry` records were added.
