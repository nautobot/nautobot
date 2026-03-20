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
 * Initialize `onFormLoad` Nautobot UI API.
 * @returns {{ addOnFormLoadListener: function(string, function(Event): void): void }} An object containing a function
 *   to enable adding a **one-per-form-ID** `listener` to be called when a form is loaded.
 */
export const initializeOnFormLoad = () => {
  const EMBEDDED_ACTION_MODAL_QUERY_SELECTOR = '#embedded_action_modal';
  const listeners = {};

  const onFormLoad = (event) => Object.values(listeners).forEach((listener) => listener(event));
  document.addEventListener('DOMContentLoaded', onFormLoad);
  if (document.querySelector(EMBEDDED_ACTION_MODAL_QUERY_SELECTOR)) {
    htmx.on(EMBEDDED_ACTION_MODAL_QUERY_SELECTOR, 'htmx:afterSettle', onFormLoad);
  }

  /**
   * Fire a `listener` callback when a form is loaded.
   * @param {string} id - Unique listener ID identifier, used to prevent registering the same listener multiple times.
   * @param {function(Event): void} listener - Callback function to be executed when a form is loaded.
   * @returns {void} Do not return any value, just add proper event listeners.
   */
  const addOnFormLoadListener = (id, listener) => {
    listeners[id] = listener;
  };

  return { addOnFormLoadListener };
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
