# Example Plugin

This is a sample plugin with all the bells and whistles that is used for unit testing plugin features. It is also provided here as an example plugin application.

## Installation

To install this example plugin from this directory run this command:

```no-highlight
$ pip install .
```

And then add it to your `PLUGINS` setting in your `nautobot_config.py`:

```python
PLUGINS = [
    "example_plugin",
]
```
