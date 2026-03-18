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

  return '';
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
