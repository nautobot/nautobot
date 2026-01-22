const INPUT_ID_TO_VALUE_REGEXP = /_option_(?<value>.*)$/;
const LIST_CLASS = 'nb-select-multiple-orderable-list';

/**
 * Initialize Nautobot `SelectMultipleOrderable` form fields to synchronize their widget list state with the underlying
 * `<select>` field.
 * @returns {function(): void} Unobserve function - disconnect all event listeners created during function call.
 */
export const initializeSelectMultipleOrderable = () => {
  /**
   * Map `<input type="checkbox">` `checked` states to `<option>` `selected` states of the underlying `<select>`
   * combobox.
   * @param {Event} event - Event object.
   */
  const onInput = (event) => {
    const input = event.target;
    const list = input.closest(`.${LIST_CLASS}`);
    if (list) {
      const value = input.id?.match(INPUT_ID_TO_VALUE_REGEXP)?.groups?.value;
      if (value) {
        const select = list.previousElementSibling;
        const option = select.querySelector(`[value="${value}"]`);
        option.selected = input.checked;
      }
    }
  };

  // Using event delegation pattern here to avoid re-creating listeners each time DOM is modified.
  document.addEventListener('input', onInput);

  return () => {
    document.removeEventListener('input', onInput);
  };
};
