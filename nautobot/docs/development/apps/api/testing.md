# Testing Apps

In general apps can be tested like other Django apps. In most cases you'll want to run your automated tests via the `nautobot-server test <app_module>` command or, if using the `coverage` Python library, `coverage run --module nautobot.core.cli test <app_module>`.

## Factories

The [`TEST_USE_FACTORIES`](../../../user-guide/administration/configuration/settings.md#test_use_factories) setting defaults to `False` when testing apps, primarily for backwards-compatibility reasons. It can prove a useful way of populating a baseline of Nautobot database data for your tests and save you the trouble of creating a large amount of baseline data yourself. We recommend adding [`factory-boy`](https://pypi.org/project/factory-boy/) to your app's development dependencies and settings `TEST_USE_FACTORIES = True` in your app's development/test `nautobot_config.py` to take advantage of this.
