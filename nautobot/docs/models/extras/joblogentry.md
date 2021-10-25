# Job Log Entry

As of Nautobot 1.2, log messages from jobs are now stored in the JobLogEntry model. This allows more performant querying of log messages and even allows viewing of logs while the job is still running.

Records of this type store the following data:

- A reference to the JobResult object that created the log.
- Timestamps indicating when the log message was created.
- The logging level of the log message.
- The log message.
- If provided, the string format of the logged object and it's absolute url.
