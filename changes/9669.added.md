Added long-term retention models for change and job history. `ArchivedObjectChange`, `ArchivedJobResult`, `ArchivedJobLogEntry` and `ArchivedJobConsoleEntry` mirror the existing `ObjectChange`, `JobResult`, `JobLogEntry` and `JobConsoleEntry` models, with every foreign key stored as a plain identifier column.
Added a database index on `JobConsoleEntry` for retrieving a job result's console output in timestamp order.
Added the `is_custom_field_model` flag to `CustomFieldModel`, which a model can set to `False` to opt out of custom field support.
