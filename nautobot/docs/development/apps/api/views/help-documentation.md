# Adding Help Documentation

If you are using the `generic.ObjectEditView` from Nautobot for your object, the form can automatically include a help icon with a link to that object's documentation. For this to happen, Nautobot must be able to find the documentation for this object in a specific directory tree within your app:

```no-highlight
app_name/                   # "nautobot_animal_sounds"
  - static/
    - app_name/             # "nautobot_animal_sounds"
      - docs/
        - index.html
        - core-data-model/
          - object_model.html  # "animal.html"
```

+/- 2.0.0
    If you have a need to deviate from this structure, your model can define as a class attribute a `documentation_static_path` string to provide a different location within the `static/` subdirectory.
