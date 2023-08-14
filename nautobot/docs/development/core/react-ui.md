# Building the React UI

## Introduction

Nautobot 2.0 introduces a new user interface built on React. This new UI will eventually be a complete replacement for the previous Django-based UI. It currently prioritizes read-only operations for core views. In subsequent releases, more operations and features will become available in this new UI.

## Design Patterns

A key change with moving to a client-side application for the user interface is that the application is now stateful. This means that the application is aware of the current state of the user interface, and can update the UI without requiring a page refresh. This is a significant change from the previous Django-based UI, which was stateless. In order to achieve this, a perspective on how the UI is rendered is required. Since much of the data is retrieved from the API, the UI is rendered in two phases:

- **Phase 1**: The UI is rendered with placeholder data, and the API is queried for the actual data
- **Phase 2**: The UI is re-rendered with the actual data

This encourages the UI to be built in a way that is resilient to changes in the data, and allows the UI to be updated without requiring a page refresh. Placeholder data can either be empty, for example on a list view this is easy: an empty list `[]`. But in more complex cases, a view may choose to show a loading indicator until the data is available.

In most cases, we build the UI with the preference we only display the final component once the data is available and display a loading indicator until then.

### State Management

The React UI is built with a concept of state management, which is handled by Redux. There is a single state store that is used to manage the state of the entire application, split into two core sections:

- **Application State**: Managed by Redux
    - Is the user logged in?
    - What is the current user?
    - What is the current page?
    - What are the models and navigation menu the user can access?
- **API State**: Managed by RTK Query (a subset library provided by Redux)
    - Previous responses to detail and list requests

These sections are known as "slices" of state, and have their own methods for updating and retrieving state. For more information on Redux, see the [Redux documentation](https://redux.js.org/).

### Hooks

The React UI uses hooks to manage state and side effects. Hooks are functions that let you "hook into" React state and lifecycle features. To learn more about hooks, see the [React Hooks documentation](https://react.dev/reference/react).

## Getting Started With Development

The libraries and tools used to build the React UI are:

- [React](https://reactjs.org/)
- [React Router](https://reactrouter.com/)
- [Chakra UI](https://chakra-ui.com/)
- [Redux](https://redux.js.org/)
- [React Redux](https://react-redux.js.org/)
- [RTK Query](https://redux-toolkit.js.org/rtk-query/overview)

### Customizing a Model's detail view

Currently, it is possible to customize the layout, groups, and fields of a detail view for a model. You can achieve this by creating groups that contain fields, which can be positioned either in the left column or the right column. To customize the detail view of your model, follow the instructions below:

```python
class ExampleModelSerializer(ModelSerializer):
    ...
    class Meta:
        ...
        detail_view_config = {
            "layout": [
                {
                    "Group Name 1": {"fields": ["name", ...]},
                    "Group Name 2": {"fields": [...]},
                },
                {
                    "Group Name 3": {"fields": [...]},
                    "Group Name 4": {"fields": [...]},
                },
            ],
            "include_others": False
        }
```

In the above example, we add the `detail_view_config` attribute to the Serializer's inner `Meta` class. The value of this attribute is a dict containing `layout` and `include_others`(optional). the `layout` is a list containing two dictionaries, each representing the two columns of the detail view. The first dictionary represents the fields in the first column, while the second dictionary represents the fields in the second column. Each dictionary consists of a key-value pair, where the key is the name of the grouping, and the value is a list of the model fields that should be included in that grouping.
The optional key `include_others`, when set to `True`, adds missing serializer fields from the `detail_view_config["layout"]` to the view_config layout.

If a `detail_view_config` is not provided to the Model Serializer, the default view configuration will be used. The default view configuration displays all non-many-to-many (non-m2m) fields in the left column, and many-to-many (m2m) fields in the right column, with each field having its own grouping.

!!! note
    `Other Fields` cannot be used as a group name as this is a reserved keyword.

### Documenting Your Code

The UI uses JS Doc to document the code. For more information on JS Doc, see the [JS Doc website](https://jsdoc.app/).

We prefer to use the `@param` and `@returns` tags to document the parameters and return values of functions. For example:

```js
/**
 * Given an API payload with session information, updates the state with the session information
 * @param {Object} state - The current state
 * @param {Object} action - The called-with payload and action type
 * @returns The updated state
 */
updateAuthStateWithSession(state, action) {
    //... 
}
```

### Linting & Formatting

#### Linting

The UI uses ESLint to lint the code. For more information on ESLint, see the [ESLint website](https://eslint.org/).

To check for linting errors, run the following command:

```shell
invoke eslint
```

To automatically fix some linting errors, run the following command:

```shell
invoke eslint -a
```

#### Formatting

The UI uses Prettier to format the code. For more information on Prettier, see the [Prettier website](https://prettier.io/).

To check for linting errors, run the following command:

```shell
invoke prettier
```

To automatically format the code, run the following command:

```shell
invoke prettier -a
```

## Additional Links

Here are some links to resources that may be helpful when working with the React UI:

- [React and Effects](https://react.dev/learn/synchronizing-with-effects)
- [RTK Query and Asynchronous Hooks](https://redux-toolkit.js.org/rtk-query/usage/queries#query-hook-options)
- [Using useDispatch](https://react-redux.js.org/api/hooks#usedispatch)
