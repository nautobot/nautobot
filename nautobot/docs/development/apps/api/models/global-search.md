# Including Models in the Global Search

+++ 2.0.0

Simply define a `searchable_models` array on the NautobotAppConfig for your app, listing the lowercase names of the model(s) from your app that you wish to include in the Nautobot global search.

```python
class AnimalSoundsConfig(NautobotAppConfig):
    ...
    searchable_models = ["animal"]
```
