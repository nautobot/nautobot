# GraphQL Queries

Nautobot provides the ability to store GraphQL queries in the database for simple maintaining and re-running.

## Saved Query Views

Navigate to Extensibility > Data Management > GraphQL Queries under the navigation bar. Located here are the views to manage saved query objects in the database.

When queries get saved to the database from the form, the query is first loaded into GraphQL to ensure that syntax is correct. If there is an issue with the query, an error message is displayed below the textarea.

## GraphiQL Interface

Modifications have been made to the GraphiQL page to allow the running, editing and saving of this model.

A dropdown button called "Queries" has been added to the GraphiQL toolbar. This lists all saved queries in the database allowing the user to open them into GraphiQL.

If a saved query has been opened, a button will appear next to the name inside the "Queries" dropdown called "Save Changes". This allows the user to save any changes to the model object.

If the user wants to create a new query, at the bottom of the "Queries" tab there is an option called "Save Current Query As...". This will open a modal form to input data, such as the name of the query, and then save the query to the database.

## API Endpoint

An API endpoint has be created to allow running of saved queries through a simple POST request.

* Request: `POST`
* URL: `{server_address}/api/extras/graphql-queries/{slug}/run/`
* Content-type: `application/json`
* Body: JSON of query variables `{"variable_1": "value_1", "variable_2": "value_2"}`
