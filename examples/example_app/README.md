# Example App

This is a sample Nautobot App with all the bells and whistles that is used for unit testing App features. It is also provided here as an example for those interested in developing their own Apps.

## Installation

To install this example App from this directory run this command:

```no-highlight
pip install .
```

And then add it to your `PLUGINS` setting in your `nautobot_config.py`:

```python
PLUGINS = [
    "example_app",
]
```
