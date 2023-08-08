# Global

## Replace the Usage of Slugs with Composite Keys

Slugs were used to identify unique objects in the database for various models in Nautobot v1.x and they are now replaced by Composite Keys. The `slug` field can be safely deleted as long as your models are derived from `BaseModel` that automatically supports the following [natural key](https://docs.djangoproject.com/en/3.2/topics/serialization#natural-keys) APIs. For a more comprehensive guideline on how Natural Keys/Composite Keys in Nautobot v2.0 works, please go to the [Natural Key documentation](../../../core/natural-keys.md).
