# Search

## Search Bar Overview

Starting with Nautobot 3.0, a globally accessible search bar is available throughout the platform. This unified search allows you to perform global or model-specific searches from any page. For example, you can search for a Device while viewing a Location, or search any `searchable` model from the Prefix view.

You can quickly open the search bar using `Cmd+K` on macOS or `Ctrl+K` on Windows.

### Search Features

- **Model-specific search:** Scope your search to a specific model using the syntax `in:$model`. Model names should be plural and use spaces for multiple words.
- **Global search:** Search across all searchable models by omitting the `in:$model` syntax.
- **Partial matches:** The search leverages the model's Q-Search capabilities, typically matching common fields using case-insensitive partial matches.
- **Feedback:** The interface provides positive feedback when searching within a model.

### Model Name Guidelines

The most common challenge is knowing the correct model name and format. Here are some examples:

#### Correct Usage

```bash
in:Devices
in:Device Types
in:prefixes     # Not case-sensitive
```

#### Incorrect Usage

```bash
in: Devices     # Space after 'in:'
in:Device       # Not plural
in:Device Type  # Not plural
in:DeviceTypes  # Missing space between words
```

!!! tip
    To find the correct model name, navigate to the model in the UI and observe its spelling.

## Which Fields Are Searchable?

The fields matched by each model's search bar are documented on the [Searchable Fields by Model](searchable-fields.md) page. When you enter a term in a model's list view search bar, Nautobot matches it against all of that model's searchable fields at once and returns any object matching at least one of them. Most fields use a case-insensitive partial match; see the linked page for the exact fields per model.
