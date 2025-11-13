import get from 'lodash.get';

/**
 * Get HTML `element`. This function accepts input as native `Document` and `Element` object and `jQuery` collection.
 * It should no longer be required after migrating away from jQuery.
 * @param {Document|Element|jQuery} `element` - `element` in question.
 * @returns {Document|Element} Native `element` object.
 */
const getElement = (element) => (element instanceof Document || element instanceof Element ? element : element[0]);

/**
 * Get `select` element value.
 * @param {HTMLSelectElement} select - `select` element in question.
 * @returns {string|string[]} `string` value for single combobox, an array of `string` values for multiple combobox.
 */
const getValue = (select) =>
  select?.getAttribute('multiple') === null ? select?.value : [...select.selectedOptions].map((option) => option.value);

/**
 * Set Select2 combobox value(s).
 * @param {HTMLSelectElement} select2 - Select2 combobox HTML element.
 * @param {{ text: string, value: string }[]|null} value - Array of objects containing `text` and `value` key-value
 *   pairs; `null` to reset the field value.
 */
export const setSelect2Value = (select2, value) => {
  $(select2).val(null);

  (value ?? []).forEach((attributes) => {
    if (!select2.querySelector(`option[value="${attributes.value}"]`)) {
      const option = document.createElement('option');
      option.innerText = attributes.text;
      option.setAttribute('selected', 'true');
      option.setAttribute('value', attributes.value);
      select2.appendChild(option);
    }
  });

  const nextValue = (() => {
    if (value.length > 0) {
      const isMultiple = select2?.getAttribute('multiple') !== null;
      return isMultiple ? value.map((attributes) => attributes.value) : value?.[0]?.value;
    }

    return null;
  })();

  $(select2).val(nextValue).trigger('change');
};

/**
 * Parse URLs which may contain variable references to other field values.
 * @param {string} url - URL template string.
 * @returns {string} URL with interpolated dynamic values.
 */
const parseURL = (url) => {
  const filter_regex = /\{\{([a-z_]+)}}/g;

  let match; // eslint-disable-line init-declarations
  let rendered_url = url;

  while ((match = filter_regex.exec(url))) {
    const filter_field = document.querySelector(`#id_${match[1]}`);
    const custom_attribute = filter_field?.selectedOptions?.[0]?.getAttribute('api-value');
    const replace =
      custom_attribute || filter_field.value || (filter_field.getAttribute('data-null-option') ? 'null' : undefined);

    rendered_url = replace ? rendered_url.replace(match[0], replace) : rendered_url;
  }

  return rendered_url;
};

/**
 * Initialize given Select2 components in passed `context` by `selector`, optionally with `options`.
 * @param {Document|Element|jQuery} context - Context root element.
 * @param {string} selector - CSS query selector of `select` elements to be initialized as Select2 components.
 * @param {object} [options] - Optional Select2 components initialization options.
 * @returns {void} Do not return any value, just initialize given Select2 components.
 */
const initializeSelect2 = (context, selector, options) =>
  [...getElement(context).querySelectorAll(selector)].forEach((element) =>
    $(element).select2({
      allowClear: true,
      placeholder: '---------',
      selectionCssClass: 'select2--small',
      theme: 'bootstrap-5',
      width: 'off',
      ...options,
    }),
  );

const initializeColorPicker = (context, dropdownParent = null) => {
  // Assign color picker selection classes.
  const colorPickerClassCopy = (data, container) => {
    if (data.element) {
      // Swap the style.
      const containerElement = getElement(container);
      containerElement.setAttribute('style', data.element.getAttribute('style'));
    }

    return data.text;
  };

  initializeSelect2(context, '.nautobot-select2-color-picker', {
    dropdownParent,
    templateResult: colorPickerClassCopy,
    templateSelection: colorPickerClassCopy,
  });
};

const initializeDynamicChoiceSelection = (context, dropdownParent = null) => {
  initializeSelect2(context, '.nautobot-select2-api', {
    ajax: {
      data: function data(params) {
        const [element] = this;

        // Paging. Note that `params.page` indexes at 1.
        const offset = (params.page - 1) * 50 || 0;

        // Base query params.
        const limit = 50;
        const q = params.term;

        // Get search query param name, defaults to `'q'`.
        const search_field = element.getAttribute('search-field') || 'q';

        // Set api_version.
        const api_version = element.getAttribute('data-api-version');

        // Allow for controlling the depth setting from within APISelect.
        const depth = parseInt(element.getAttribute('data-depth'), 10) || 0;

        // Attach content_type to parameters.
        const content_type = element.getAttribute('data-contenttype');

        // Attach any extra query parameters
        const extra_query_parameters_array = [...element.attributes]
          .filter((attribute) => attribute.name.includes('data-query-param-'))
          .flatMap((attribute) => {
            const [, param_name] = attribute.name.split('data-query-param-');

            const values = (() => {
              try {
                return JSON.parse(attribute.value);
                // eslint-disable-next-line no-unused-vars
              } catch (exception) {
                return [];
              }
            })();

            return values.flatMap((value) => {
              const has_ref_field = value.startsWith('$');

              // Referencing the value of another form field.
              const ref_field = has_ref_field
                ? (() => {
                    const name = value.slice(1);

                    if (element.id.includes('id_form-')) {
                      const [id_prefix] = element.id.match(/id_form-[0-9]+-/i, '');
                      return document.querySelector(`#${id_prefix}${name}`);
                    }

                    /*
                     * If the element is in a table row with a class containing "dynamic-formset" we need to find the
                     * reference field in the same row.
                     */
                    if (element.closest('tr')?.classList.contains('dynamic-formset')) {
                      return element.closest('tr').querySelector(`select[id*="${name}"]`);
                    }

                    return document.querySelector(`#id_${name}`);
                  })()
                : null;

              const ref_field_value = ref_field
                ? (() => {
                    const field_value = getValue(ref_field);
                    const style = window.getComputedStyle(ref_field);

                    if (field_value && style.opacity !== '0' && style.visibility !== 'hidden') {
                      return field_value;
                    }

                    if (ref_field.getAttribute('required') && ref_field.getAttribute('data-null-option')) {
                      return 'null';
                    }

                    return undefined;
                  })()
                : null;

              const param_value = has_ref_field ? ref_field_value : value;
              return param_value !== null && param_value !== undefined ? [[param_name, ref_field_value || value]] : [];
            });
          });

        const parameters = [
          ['depth', String(depth)],
          ['limit', String(limit)],
          ['offset', String(offset)],
          ...(api_version ? [['api_version', api_version]] : []),
          ...(content_type ? [['content_type', content_type]] : []),
          ...(q ? [[search_field, q]] : []),
          ...extra_query_parameters_array,
        ];

        // This will handle params with multiple values (i.e. for list filter forms).
        return new URLSearchParams(parameters).toString();
      },
      delay: 500,
      processResults: function processResults(data) {
        const [element] = this.$element;
        [...element.querySelectorAll('option')].forEach((child) => child.removeAttribute('disabled'));

        const results = [
          // Handle the null option, but only add it once.
          ...(element.getAttribute('data-null-option') && data.previous === null
            ? [{ id: 'null', text: element.getAttribute('data-null-option') }]
            : []),
          ...Object.values(
            data.results.reduce((accumulator, record, index) => {
              // The disabled-indicator equated to true, so we disable this option.
              const disabled = Boolean(record?.[element.getAttribute('disabled-indicator')]);
              const id = get(record, element.getAttribute('value-field')) || record.id;
              const text = get(record, element.getAttribute('display-field')) || record.name;

              const item = { ...record, disabled, id, text };
              const { group, site, url } = item;

              /*
               * `DynamicGroupSerializer` has a `children` field which fits an inappropriate if condition in
               * `select2.min.js`, which will result in the incorrect rendering of `DynamicGroup` `DynamicChoiceField`.
               * So we nullify the field here since we do not need this field.
               */
              const should_nullify_children = Boolean(url?.includes('dynamic-groups'));

              const collection = (() => {
                switch (true) {
                  case group !== undefined && group !== null && site !== undefined && site !== null:
                    return { property: `${site.name}:${group.name}`, text: `${site.name} / ${group.name}` };

                  case group !== undefined && group !== null:
                    return { property: group.name, text: group.name };

                  case site !== undefined && site !== null:
                    return { property: site.name, text: site.name };

                  case group === null && site === null:
                    return { property: 'global', text: 'Global' };

                  default:
                    return undefined;
                }
              })();

              return {
                ...accumulator,
                ...(collection
                  ? {
                      [collection.property]: {
                        ...accumulator[collection.property],
                        ...(accumulator[collection.property] ? undefined : { text: collection.text }),
                        children: should_nullify_children
                          ? undefined
                          : [...(accumulator[collection.property]?.children ?? []), item],
                      },
                    }
                  : { [index]: item }),
              };
            }, {}),
          ),
        ];

        // Check if there are more results to page.
        const has_next_page = data.next !== null;
        return { pagination: { more: has_next_page }, results };
      },
      url: function url() {
        const [element] = this;
        const dataUrl = parseURL(element.getAttribute('data-url'));

        // If URL is not fully rendered yet, abort the request.
        return !dataUrl.includes('{{') && dataUrl;
      },
    },
    dropdownParent,
  });
};

const initializeMultiValueChar = (context, dropdownParent = null) => {
  initializeSelect2(context, '.nautobot-select2-multi-value-char', {
    dropdownParent,
    language: { noResults: () => 'Type something to add it as an option' },
    multiple: true,
    tags: true,
    tokenSeparators: [','],
  });

  // Ensure pressing Enter in the Select2 search adds the current token instead of submitting the form
  [...getElement(context).querySelectorAll('.nautobot-select2-multi-value-char')].forEach((element) => {
    $(element).on('select2:open', () => {
      const container = document.querySelector('.select2-container--open');
      if (!container) {
        return;
      }
      const search = container.querySelector('input.select2-search__field');
      if (!search) {
        return;
      }

      // Avoid stacking multiple handlers
      if (search.getAttribute('data-enter-binds')) {
        return;
      }
      search.setAttribute('data-enter-binds', '1');

      search.addEventListener('keydown', (ev) => {
        if (ev.key === 'Enter') {
          ev.preventDefault();
          ev.stopPropagation();
          const val = search.value.trim();
          if (!val) {
            return;
          }
          const sel = $(element).get(0);
          // If option doesn't exist, create it; otherwise select it
          const found = Array.prototype.find.call(sel.options, (opt) => String(opt.value) === String(val));
          if (found) {
            found.selected = true;
          } else {
            sel.add(new Option(val, val, true, true));
          }
          // Clear the search box and notify Select2
          search.value = '';
          $(element).trigger('change');
          // Close the dropdown so it doesn't linger after add
          try {
            $(element).select2('close');
            // eslint-disable-next-line no-unused-vars
          } catch (exception) {
            // Intentional no-op
          }
        }
      });
    });
  });
};

const initializeStaticChoiceSelection = (context, dropdownParent = null) =>
  initializeSelect2(context, '.nautobot-select2-static', { dropdownParent });

export const initializeSelect2Fields = (context) => {
  initializeColorPicker(context);
  initializeDynamicChoiceSelection(context);
  initializeMultiValueChar(context);
  initializeStaticChoiceSelection(context);

  [...getElement(context).querySelectorAll('.modal')].forEach((modal) => {
    initializeColorPicker(modal, modal);
    initializeDynamicChoiceSelection(modal, modal);
    initializeMultiValueChar(modal, modal);
    initializeStaticChoiceSelection(modal, modal);
  });
};
