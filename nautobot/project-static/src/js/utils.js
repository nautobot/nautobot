/**
 * This function is heavily inspired by React `createElement`. Its purpose is to remove some boilerplate code otherwise
 * required for creating new HTML elements.
 * @example
 * // Create `row` and `col` elements with a valid parent-child relationship.
 * const child = createElement('div', { className: 'col' });
 * const parent = createElement('div', { className: 'row' }, child);
 * @param {string} tag - HTML element tag name to be passed to `document.createElement` function.
 * @param {object} [attributes={}] - Object containing HTML element attributes to be set on newly created HTML element.
 *   `class` attribute is a special case in which `className` property name can be optionally used in order to avoid
 *   ambiguation with JavaScript reserved `class` keyword.
 * @param {(HTMLElement|string)} [children] - HTML elements or string values to become newly created element children.
 * @returns {HTMLElement} New HTML element. Append it to an existing DOM node if you want it to appear in browser.
 */
export const createElement = (tag, attributes = {}, ...children) => {
  const element = document.createElement(tag);

  Object.entries(attributes).forEach(([attribute, value]) =>
    element.setAttribute(attribute === 'className' ? 'class' : attribute, value),
  );

  children.forEach((child) =>
    typeof child === 'string' ? element.insertAdjacentText('beforeend', child) : element.appendChild(child),
  );

  return element;
};

/**
 * Remove all classes from given element, optionally excluding some explicitly.
 * @example
 * // Remove all classes except `container-fluid` from given element.
 * removeElementClasses(element, 'container-fluid');
 * @param {HTMLElement} element - HTML element which classes are to be removed.
 * @param {string} [ignore] - Classes to ignore during class removal, i.e. should be left as-is.
 * @returns {void} Do not return any value, modify existing HTML element in-place.
 */
export const removeElementClasses = (element, ...ignore) =>
  [...element.classList.entries()]
    .filter(([, className]) => !ignore.includes(className))
    .forEach(([, className]) => element.classList.remove(className));

/**
 * Convert `px` pixel value to `rem` units.
 * @example
 * // Convert `20` (`px`) to `rem`, return `1.25` (`rem`).
 * rem(20);
 * @param {number} px - Pixel value.
 * @returns {number} Given pixel value converted to `rem` units.
 */
export const rem = (px) => {
  const rootFontSize = window.getComputedStyle(document.documentElement).fontSize;
  return px / parseInt(rootFontSize, 10);
};
