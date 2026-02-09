/**
 * Function to get "Lookup type" field
 * @returns {Element}
 */
const typeFieldGetter = () => document.getElementById('nb-add-filter-form').querySelector('[name$="lookup_type"]')

/**
 * Function to get "Value" field
 * @returns {Element}
 */
const valueFieldGetter = () => (
  [...document.getElementById('nb-add-filter-form').querySelectorAll('.nb-add-filter-form-field')]
    .pop()
    ?.querySelector('input, select, textarea')
)

/**
 * Insert given `element` as `parent`'s first child.
 * @param {HTMLElement} element - Element to be inserted.
 * @param {HTMLElement} parent - Parent container for given `element`.
 * @returns {void} Do not return any value, modify DOM in-place.
 */
const insertFirst = (element, parent) => {
  parent.hasChildNodes() ? parent.insertBefore(element, parent.firstElementChild) : parent.appendChild(element);
};

/**
 * Helper method to create remove button on dynamic filters
 * @param label
 * @returns {HTMLButtonElement}
 */
const removeButton = (label) => {
  const button = document.createElement('button');
  button.classList.toggle('nb-dynamic-filter-remove', true);
  button.setAttribute('type', 'button');
  button.appendChild(closeIcon());
  button.appendChild(buttonLabel(label));
  return button
}

/**
 * Helper method to create required label for remove button on dynamic filters
 * @param labelText
 * @returns {HTMLSpanElement}
 */
const buttonLabel = (labelText) => {
  const label = document.createElement('span');
  label.classList.toggle('visually-hidden', true);
  label.innerText = labelText;
  return label
}

/**
 * Helper method to create close icon for remove button on dynamic filters
 * @returns {HTMLSpanElement}
 */
const closeIcon = () => {
  const close = document.createElement('span');
  close.classList.toggle('mdi', true);
  close.classList.toggle('mdi-close', true);
  close.setAttribute('aria-hidden', 'true');
  return close
}

/**
 * Synchronize given `filter` value from default to dynamic filter form.
 * @param {string} name - Filter name.
 * @returns {void} Do not return any value, just set given field values.
 */
const syncDefaultToDynamic = (name) => {
  const {defaultFilterForm} = getFilterForms();

  const field = defaultFilterForm.querySelector(`[name="${name}"]`);
  const text = field?.closest('.nb-form-group')?.querySelector('label')?.innerText?.trim();
  /*
   * `manageDynamicFilter` takes an array of `{ text: string, value: string }` objects as `value`, so
   * regardless of field being a textbox, a single or multiple choice combobox, conversion is required:
   *   1. For combobox (i.e. `<select>`), iterate over selected options and map them to display `text`
   *     and underlying `value`.
   *   2. For textbox (i.e. `<input>` or `<textarea>`):
   *     1. Use entered value as both display `text` and underlying `value`.
   *     2. If field is empty, use an empty array.
   */
  const value =
    field?.tagName === 'SELECT'
      ? [...field.selectedOptions].map((option) => ({text: option.innerText, value: option.value}))
      : [...(field?.value ? [{text: field.value, value: field.value}] : [])];

  manageDynamicFilter({action: 'set', name, text, value});
};

/**
 * Synchronize given `filter` value from dynamic to default filter form.
 * @param {string} name - Filter name.
 * @returns {void} Do not return any value, just set given field values.
 */
const syncDynamicToDefault = (name) => {
  const {defaultFilterForm, dynamicFilterForm} = getFilterForms();

  const current = [...dynamicFilterForm.querySelectorAll(`input[name="${name}"][type="hidden"]`)].map(
    (input) => ({
      text: [...(input.parentElement?.childNodes ?? [])].find((node) => node.nodeName === '#text')?.wholeText,
      value: input.getAttribute('value'),
    }),
  );

  const sync = defaultFilterForm?.querySelector(`[name=${name}]`);

  if (sync?.tagName === 'INPUT' || sync?.tagName === 'TEXTAREA') {
    sync.value = current.length > 0 ? current[0].value : '';
  } else if (sync?.tagName === 'SELECT') {
    window.nb.select2.setSelect2Value(sync, current);
  }
};

/**
 * Manage dynamic filter either by adding values to the existing selection or by setting passed values
 * regardless of previous selection.
 * @param {'add'|'set'} action - Use `'add'` to add given value to the existing selection; use `'set'`
 *   to set given value regardless of what was set previously.
 * @param {string} name - Filter field name.
 * @param {string} text - Filter display text.
 * @param {object[]} value - Array of objects containing `text` and `value` key-value pairs.
 */
const manageDynamicFilter = ({action, name, text, value}) => {
  const {dynamicFilterForm} = getFilterForms();
  const items = dynamicFilterForm.querySelector('.nb-dynamic-filter-items');

  const group = (() => {
    const existing = items.querySelector(`.nb-multi-badge[data-nb-field="${name}"]`);
    if (existing) {
      return existing;
    }

    const group = document.createElement('span');
    group.classList.toggle('badge', true);
    group.classList.toggle('nb-multi-badge', true);
    group.setAttribute('data-nb-field', name);

    const children = document.createElement('span');
    children.classList.toggle('nb-multi-badge-items', true);

    group.appendChild(removeButton('Remove All'));
    group.insertAdjacentText('beforeend', `${text}:`);
    group.appendChild(children);

    return group;
  })();

  const children = group.querySelector('.nb-multi-badge-items');
  const existing = [...children.querySelectorAll('.badge[data-nb-value]')];

  /*
   * Depending on `action` remove the following badges:
   *   1. For `'add'`, remove already existing filters with the same key-value pairs and re-create them later.
   *   2. For `'set'`, remove all existing filters of given key and apply only these passed as `values`.
   */
  const badgesToRemove =
    action === 'add'
      ? existing.filter((badge) => value.some((item) => badge.getAttribute('data-nb-value') === item.value))
      : existing;
  badgesToRemove.forEach((item) => children.removeChild(item));

  value.forEach(({text, value}) => {
    const badge = document.createElement('span');
    badge.classList.toggle('badge', true);
    badge.setAttribute('data-nb-value', value);

    const input = document.createElement('input');
    setInputName(input, name)
    input.setAttribute('type', 'hidden');
    input.setAttribute('value', value);

    badge.appendChild(removeButton('Remove'));
    badge.insertAdjacentText('beforeend', text);
    badge.appendChild(input);

    insertFirst(badge, children);
  });

  // If group already exists, remove it and later insert as the first child.
  if (items.contains(group)) {
    items.removeChild(group);
  }

  if (children.hasChildNodes()) {
    insertFirst(group, items);
  }
};

document.addEventListener('DOMContentLoaded', () => {
  /**
   * Handle `Add filter` button click or `remove` buttons from added dynamic filters.
   */
  document.addEventListener('click', (event) => {
    const {defaultFilterForm, dynamicFilterForm} = getFilterForms();

    const add = event.target.closest('button.nb-dynamic-filter-add');
    if (add) {
      const field = dynamicFilterForm.querySelector('[name$="lookup_field"]');
      const type = dynamicFilterForm.querySelector('[name$="lookup_type"]');
      const value = valueFieldGetter();

      const isMissing = (control) =>
        control?.selectedOptions ? control.selectedOptions.length === 0 : !control?.value;
      if (isMissing(field) || isMissing(type) || isMissing(value)) {
        // Return early if selected filter is not complete (i.e. is missing lookup field, type or value).
        return;
      }

      const name = type.selectedOptions[0].value;
      const label = field.selectedOptions[0].innerText.trim();
      const suffix = type.selectedOptions[0].innerText.trim();
      const text = /\(\w+\)/.test(suffix) ? `${label} ${suffix}` : label;
      const values =
        value?.getAttribute('multiple') !== null
          ? [...value.selectedOptions].map((option) => ({text: option.innerText.trim(), value: option.value}))
          : [{text: value?.value, value: value?.value}];

      // If field exists in default filter form and is a single value input, use `'set'` action.
      const action =
        defaultFilterForm.querySelector(`[name="${name}"]`) &&
        (value.tagName === 'INPUT' || value.tagName === 'TEXTAREA')
          ? 'set'
          : 'add';
      manageDynamicFilter({action, name, text, value: values});

      syncDynamicToDefault(name);
    }

    const remove = event.target.closest('button.nb-dynamic-filter-remove');
    if (remove) {
      const badge = remove.closest('.badge');
      /*
       * Remove the group badge (i.e. multi-badge) when given badge is the group badge itself, or it is the only
       * one left in the group (i.e. has no siblings) because removing it will leave the group badge empty anyway.
       */
      const shouldRemoveGroup =
        badge?.classList.contains('nb-multi-badge') ||
        (!badge?.previousElementSibling && !badge?.nextElementSibling);
      shouldRemoveGroup ? badge?.closest('.nb-multi-badge')?.remove() : badge?.remove();

      syncDynamicToDefault(badge?.querySelector('input[type="hidden"]')?.getAttribute('name'));
    }
  });

  // Need to wrap `document` with jQuery to be able to listen to Select2 `change` event.
  $(document).on('change', (event) => {
    const {defaultFilterForm} = getFilterForms();
    const isDefaultFilterFormField = event.target.form === defaultFilterForm;
    if (isDefaultFilterFormField) {
      syncDefaultToDynamic(event.target.name);
    }
  });

  /**
   * Populate `value` field with data fetched from API endpoint.
   * Need to wrap `document` with jQuery to be able to listen to Select2 `change` event.
   */
  $(document).on('change', async (event) => {
    const isLookupType = event.target.getAttribute('name')?.endsWith('lookup_type');
    if (isLookupType) {
      const content_type = event.target.getAttribute('data-contenttype');
      const field_name = event.target.value;
      const value = valueFieldGetter();

      if (field_name) {
        const replacement = await (async () => {
          try {
            const response = await window.fetch(
              `/api/ui/core/filterset-fields/lookup-value-dom-element/?${new URLSearchParams({
                content_type,
                field_name
              })}`,
              {method: 'GET', headers: {Accept: '*/*'}},
            );

            const html = await response.json();

            const element = document.createElement('div');
            element.innerHTML = html;

            return element.firstElementChild;
          } catch (exception) {
            // Default to `<input type="text" ...>` field if error occurs.
            const input = document.createElement('input');
            input.classList.toggle('lookup_value-input', true);
            input.classList.toggle('form-control', true);
            input.setAttribute('id', `id_for_${field_name}`);
            input.setAttribute('name', field_name);
            input.setAttribute('type', 'text');
            return input;
          }
        })();

        value.replaceWith(replacement);
        replacement.nextElementSibling?.remove(); // Remove Select2 widget if present.
        replacement.previousElementSibling?.setAttribute('for', replacement.getAttribute('id')); // Set label `for` attribute to match field `id`.

        reInitialize(replacement.parentElement);
      }
    }
  });


  /**
   * Reset `lookup type` and `value` field if `field` is changed; or just `value` if only lookup type is changed.
   * Need to wrap `document` with jQuery to be able to listen to Select2 `change` event.
   */
  $(document).on('change', (event) => {
    const isLookupField = event.target.getAttribute('name')?.endsWith('lookup_field');
    const isLookupType = event.target.getAttribute('name')?.endsWith('lookup_type');

    if (isLookupField) {
      const type = typeFieldGetter();
      $(type).val(null).trigger('change');
    }

    if (isLookupField || isLookupType) {
      const value = valueFieldGetter();

      if (value.tagName === 'SELECT') {
        $(value).val(null).trigger('change');
      } else {
        value.value = '';
      }
    }
  });
});
