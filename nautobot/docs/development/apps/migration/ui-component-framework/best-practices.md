# Best Practices for Migration

1. **Incremental Migration**
   - Migrate one view at a time
   - Test thoroughly after each conversion
   - Keep backup of template-based views

2. **Panel Organization**
   - Use weights relative to the `Panel.`WEIGHT_*_PANEL` constants for consistency.
   - Group related panels together

3. **Performance Considerations**
   - Use select_related/prefetch_related in ObjectsTablePanel (though note that BaseTable may handle some simple optimizations automatically)
   - Optimize StatsPanel queries
   - Cache complex transformations

4. **Common Patterns**

```python
# Statistics and related objects
StatsPanel(
    filter_name="device_type",
    related_models=[Device],
    section=SectionChoices.RIGHT_HALF,
    weight=100,
)

# Custom fields grouping
GroupedKeyValueTablePanel(
    body_id="custom-fields",
    data=self.get_custom_field_groups(),
    section=SectionChoices.FULL_WIDTH,
    weight=200,
)

# Description with markdown
ObjectTextPanel(
    object_field="description",
    render_as=BaseTextPanel.RenderOptions.MARKDOWN,
    section=SectionChoices.FULL_WIDTH,
    weight=300,
)
```