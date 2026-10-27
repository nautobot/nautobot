Fixed Job object variables, and the objects that job button receivers act on, accepting objects that the user submitting the job did not have permission to view, which also revealed whether such objects existed.
Fixed the REST API's dry run of a scheduled job not enforcing the constraints of the requesting user's permission to view scheduled jobs.
