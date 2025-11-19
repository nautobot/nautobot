/**
 * Get given cookie, based on MDN example: https://developer.mozilla.org/en-US/docs/Web/API/Document/cookie#example_2_get_a_sample_cookie_named_test2
 * @param {string} name - Cookie name.
 * @returns {string|undefined} Cookie value.
 */
export const getCookie = (name) =>
  document.cookie
    .split('; ')
    .find((cookie) => cookie.startsWith(`${name}=`))
    ?.split('=')[1];

/**
 * Set given cookie `value` with optional `options`.
 * @param {string} name - Cookie name.
 * @param {string} value - Cookie value.
 * @param {object} [options] - Cookie properties as key-value pairs, e.g. `path`, `expires`, etc.
 * @returns {void} Do not return any value, modify existing document cookies in-place.
 */
export const setCookie = (name, value, options) => {
  const properties = { [name]: value, path: '/', ...options };
  document.cookie = Object.entries(properties)
    .map((entry) => entry.join('='))
    .join(';');
};

/**
 * Remove given cookie.
 * @param {string} name - Cookie name.
 * @returns {void} Do not return any value, modify existing document cookies in-place.
 */
export const removeCookie = (name) => setCookie(name, '', { expires: 'Thu, 01 Jan 1970 00:00:00 GMT' });
