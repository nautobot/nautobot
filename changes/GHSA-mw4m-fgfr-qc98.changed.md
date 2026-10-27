Changed Job object variables to accept, in the Job form and the REST API, only objects that the user submitting the job has permission to view.
Changed job button receivers to act only on objects of a type that one of their enabled job buttons applies to; App tests that run a job button receiver directly may need to create a `JobButton` for that job and content type.
