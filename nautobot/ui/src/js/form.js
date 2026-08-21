import htmx from 'htmx.org';

/**
 * Get form field ID by emulating Django `BoundField.auto_id` @property function in JavaScript.
 * Source: https://github.com/django/django/blob/4b2b4bf0ac2707dc9c4d51cabfa72168eaea95fe/django/forms/boundfield.py#L243-L255
 * @param {string} formAutoId - Django form `auto_id` property.
 * @param {string} name - Field name.
 * @param {boolean} querySelector - Return field ID in query selector format, i.e. prefixed with `'#'`. For the sake of
 *   convenience this options is enabled by default.
 * @returns {string} - Form field ID.
 */
export const getFieldAutoId = (formAutoId, name, querySelector = true) => {
  if (formAutoId?.includes('%s')) {
    const fieldAutoId = formAutoId.replace('%s', name);
    return querySelector ? `#${fieldAutoId}` : fieldAutoId;
  }

  if (formAutoId === 'True') {
    return querySelector ? `#${name}` : name;
  }

  // eslint-disable-next-line no-console
  console.error(`Cannot get field \`auto_id\` for \`"${name}"\` because the form \`auto_id\` is not defined.`);
  return '';
};

/**
 * Initialize form events Nautobot UI API. Add `'nb-form:load:{{ obj_type }}'` event dispatchers to all
 * create/edit/update forms.
 * @returns {function(): void} Destructor function - remove all event listeners added during initialization.
 */
export const initializeFormEvents = () => {
  const dispatchFormLoadEvent = (form) => {
    if (form?.tagName === 'FORM') {
      const type = `nb-form:load:${form.getAttribute('data-nb-obj-type')}`;
      // Use `setTimeout` to defer event dispatcher for one cycle, making sure all other "parallel" events have executed.
      setTimeout(() => form.dispatchEvent(new CustomEvent(type, { bubbles: true, cancelable: true })));
    }
  };

  // `'DOMContentLoaded'` handles the case when form is rendered on the main page.
  const onDOMContentLoaded = () => {
    const form = document.querySelector('#nb-create-form');
    if (form) {
      dispatchFormLoadEvent(form);
    }
  };
  document.addEventListener('DOMContentLoaded', onDOMContentLoaded);

  // `'htmx:afterSettle'` handles the case when form is rendered asynchronously with htmx, e.g. in embedded action modal.
  const onHtmxAfterSettle = (event) => {
    const { target } = event.detail;
    if (target.closest('#embedded_action_modal') && target.classList.contains('modal-content')) {
      dispatchFormLoadEvent(target.querySelector('form'));
    }
  };
  htmx.on('htmx:afterSettle', onHtmxAfterSettle);

  return () => {
    document.removeEventListener('DOMContentLoaded', onDOMContentLoaded);
    htmx.off('htmx:afterSettle', onHtmxAfterSettle);
  };
};

/**
 * Observe pinned state of elements of class `nb-form-sticky-footer` on the page and add drop shadow with `nb-is-pinned`
 * class if they are pinned. This is purely cosmetic and does not affect functionality.
 * @example
 * // Run form sticky footers observer algorithm exactly once, i.e. observe and immediately unobserve.
 * const unobserveFormStickyFooters = observeFormStickyFooters();
 * unobserveFormStickyFooters();
 * @returns {function(): void} Unobserve function - disconnect all resize observers created during function call.
 */
export const observeFormStickyFooters = () => {
  // Form sticky footers pinned state detection with `IntersectionObserver` based on: https://stackoverflow.com/a/57991537.
  const intersectionObserver = new IntersectionObserver(
    ([entry]) => entry.target.classList.toggle('nb-is-pinned', entry.intersectionRatio < 1),
    { threshold: [1] },
  );

  const formStickyFooters = [...document.querySelectorAll('.nb-form-sticky-footer')];
  formStickyFooters.forEach((formStickyFooter) => intersectionObserver.observe(formStickyFooter));

  return () => {
    intersectionObserver.disconnect();
  };
};
