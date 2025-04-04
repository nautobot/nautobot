# Best Practices for Migration

1. Incremental Migration
    - Migrate one view at a time
    - Test thoroughly after each conversion
    - Keep backup of template-based views

2. Panel Organization
    - Use weights relative to the `Panel.WEIGHT_*_PANEL` constants for consistency.
    - Group related panels together

3. Performance Considerations
    - Use `select_related`/`prefetch_related` in `ObjectsTablePanel` (though note that `BaseTable` may handle some simple optimizations automatically)
    - Optimize `StatsPanel` queries in terms of selecting proper fields and relations for counting
    - Cache complex transformations

4. Common Patterns

Statistics and related objects

```python

StatsPanel(
    weight=100,
    section=SectionChoices.RIGHT_HALF,
    filter_name="device_type",
    related_models=[Device],
)
```

`StatsPanel` for `DeviceType` model showing the stats of related `Device` (taken from `related_models`)
calculated by `count_related(Device, "device_type")` filtered by given `filter_name`

---

```python

# Custom fields grouping
GroupedKeyValueTablePanel(
    weight=200,
    section=SectionChoices.FULL_WIDTH,
    body_id="custom-fields",
    data=self.get_custom_field_groups(),
)

# Description with markdown
ObjectTextPanel(
    weight=300,
    section=SectionChoices.FULL_WIDTH,
    object_field="description",
    render_as=BaseTextPanel.RenderOptions.MARKDOWN,
)
```
