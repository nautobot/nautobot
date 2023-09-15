# Overriding Default Model Views in Nautobot Apps

+++ 2.0.0

In UI 2.0, Nautobot provides default model views (`ObjectListView`, `ObjectRetrieveView` and etc) for every model including App provided models unless they are explicitly overridden. For example, an app called `your_example_app` wants to override the default `ObjectRetrieveView` for its model called `YourExampleModel` with a customized view called `YourExampleView`. We need to go to the `index.js` file located in the `your_example_app/ui` folder and add a key `view_overrides` to the `app_config` dictionary variable.

```no-highlight
const app_config = {
    ...
    view_overrides: {}
    ...
}
```

In `view_overrides`'s dictionary, you need to specify the app and the model you want to override the default view for in this format `{app_label}: {model_name}`. So in our case, it would be `"your-example-app": "your-example-model"`.

```no-highlight
...
    view_overrides: {
        "your-example-app": "your-example-model": {}
    }
...
```

Finally, you need to specify the default view action you want to override and the new view in this format `{view_action}: {new_view}`. So in our case, it would be `"retrieve": "YourExampleView"`:

```no-highlight
...
    view_overrides: {
        "your-example-app": "your-example-model": {
            "retrieve": "YourExampleView"
        }
    }
...
```

Now if you go to `YourExampleModel`'s retrieve view, instead of the default `ObjectRetrieveView`, you will see the customized layout of `YourExampleView`.

If you want to override the default `ObjectListView` as well for `YourExampleModel` with `YourExampleListView`, just append `"list": "YourExampleListView"` to the `"your-example-app": "your-example-model"` dictionary.

```no-highlight
...
    view_overrides: {
        "your-example-app": "your-example-model": {
            "retrieve": "YourExampleView",
            "list": "YourExampleListView",
        }
    }
...
```
