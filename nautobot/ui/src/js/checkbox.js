const ITEM_CHECKBOX_SELECTOR = 'input[type="checkbox"][name="pk"]';
const TOGGLE_CHECKBOX_SELECTOR = 'input[type="checkbox"].toggle';
const SELECT_ALL_BOX_SELECTOR = '#select_all_box';
const SELECT_ALL_CHECKBOX_SELECTOR = '#select_all';

/**
 * Set checkbox `checked` state while dispatching proper events. Do nothing if `checkbox.checked` state is already the
 * same as passed `checked` parameter.
 * @param {HTMLInputElement} checkbox - Checkbox HTML element.
 * @param {boolean} checked - `checked` state to be set.
 * @returns {void} Do not return any value, set given HTML element state and dispatch `'change'` and `'input'` events.
 */
const setChecked = (checkbox, checked) => {
  if (checkbox.checked !== checked) {
    checkbox.checked = checked;
    // Defer dispatching events with `setTimeout` to prevent handling intermediate states during sequential updates.
    setTimeout(() => {
      checkbox.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
      checkbox.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
    });
  }
};

/**
 * Initialize custom logic handlers for `class="toggle ..."`, `name="pk"` and `id="select-all" checkboxes.
 * @returns {void} Do not return any value, just initialize proper custom logic handlers for specific checkboxes.
 */
export const initializeCheckboxes = () => {
  // Track the last selected checkbox index for range selection.
  let lastSelectedIndex = null;

  /*
   * `onClick` and `onInput` event handlers both act on the same checkbox elements, but in slightly different scenarios:
   *   1. `onClick` is specifically tied to manual user interaction and is called only when user directly interacts with
   *      checkbox element. It handles:
   *        1.1. Checking/unchecking all individual checkboxes in the table when "toggle" checkbox is clicked.
   *        1.2. Shift-click range selection for individual checkboxes in the table.
   *   2. `onInput` is called after checkbox state is changed, regardless of the change being triggered programmatically
   *       or by manual user interaction. It handles:
   *         2.1. Showing/hiding "select all" box when "toggle" checkbox is checked/unchecked.
   *         2.2. Checking/unchecking "toggle" checkbox based on the collective state of individual checkboxes.
   *         2.3. Enabling/disabling buttons in "select all" box based on its checkbox state.
   */
  const onClick = (event) => {
    // "Toggle" checkbox for object lists (PK column). Notice distinction between handling `'click'` and `'input'` events.
    const toggleCheckbox = event.target.closest(TOGGLE_CHECKBOX_SELECTOR);
    if (toggleCheckbox) {
      const isChecked = toggleCheckbox.checked;

      // Check/uncheck all PK column checkboxes in the table.
      toggleCheckbox
        .closest('table')
        .querySelectorAll(`${ITEM_CHECKBOX_SELECTOR}:not(.visually-hidden)`)
        .forEach((checkbox) => setChecked(checkbox, isChecked));

      // Reset last selected index when using toggle all
      lastSelectedIndex = null;
    }

    // Individual row item checkbox in object lists (PK column). Notice distinction between handling `'click'` and `'input'` events.
    const itemCheckbox = event.target.closest(ITEM_CHECKBOX_SELECTOR);
    if (itemCheckbox) {
      const table = itemCheckbox.closest('table');
      const allCheckboxes = [...table.querySelectorAll(`${ITEM_CHECKBOX_SELECTOR}:not(.visually-hidden)`)];
      const currentIndex = allCheckboxes.indexOf(itemCheckbox);

      // Handle shift-click for range selection/deselection in PK column.
      if (event.shiftKey && lastSelectedIndex !== null) {
        // Create range from previous click to current click
        const startIndex = Math.min(lastSelectedIndex, currentIndex);
        const endIndex = Math.max(lastSelectedIndex, currentIndex);

        // Use the clicked item's new state for entire range
        const shouldSelect = itemCheckbox.checked;

        // Apply to entire range
        allCheckboxes.slice(startIndex, endIndex + 1).forEach((checkbox) => setChecked(checkbox, shouldSelect));
      }

      // Always update anchor to current click (normal click or shift+click)
      lastSelectedIndex = currentIndex;
    }
  };

  const onInput = (event) => {
    // "Toggle" checkbox for object lists (PK column). Notice distinction between handling `'click'` and `'input'` events.
    const toggleCheckbox = event.target.closest(TOGGLE_CHECKBOX_SELECTOR);
    if (toggleCheckbox) {
      const isChecked = toggleCheckbox.checked;

      // Show/hide the select all objects form that contains the bulk action buttons.
      const selectAllBox = document.querySelector(SELECT_ALL_BOX_SELECTOR);
      selectAllBox?.classList.toggle('visually-hidden', !isChecked);

      if (selectAllBox && !isChecked) {
        const selectAll = document.querySelector(SELECT_ALL_CHECKBOX_SELECTOR);
        if (selectAll) {
          setChecked(selectAll, false);
        }
      }
    }

    // Individual row item checkbox in object lists (PK column). Notice distinction between handling `'click'` and `'input'` events.
    const itemCheckbox = event.target.closest(ITEM_CHECKBOX_SELECTOR);
    if (itemCheckbox) {
      const table = itemCheckbox.closest('table');
      const allCheckboxes = [...table.querySelectorAll(`${ITEM_CHECKBOX_SELECTOR}:not(.visually-hidden)`)];

      // Check or uncheck the "toggle" checkbox if all items are checked or any item is unchecked, respectively.
      const tableToggleCheckbox = table.querySelector(TOGGLE_CHECKBOX_SELECTOR);
      if (tableToggleCheckbox) {
        const hasUnchecked = allCheckboxes.some((checkbox) => !checkbox.checked);
        setChecked(tableToggleCheckbox, !hasUnchecked);
      }
    }

    // `selectAll` is the checkbox that selects all objects.
    const selectAll = event.target.closest(SELECT_ALL_CHECKBOX_SELECTOR);
    // `selectAllBox` is the form bulk action buttons container.
    const selectAllBox = event.target.closest(SELECT_ALL_BOX_SELECTOR);
    if (selectAll && selectAllBox) {
      // If the `selectAll` checkbox is checked, enable all form bulk action buttons.
      const isChecked = selectAll.checked;
      selectAllBox.querySelectorAll('button').forEach((button) => {
        button.disabled = !isChecked;
      });
    }
  };

  document.addEventListener('click', onClick);
  document.addEventListener('input', onInput);
};
