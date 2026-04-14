import htmx from 'htmx.org';

/**
 * Refresh Django messages on the page using HTMX swap.
 * @param {string} url - HTMX AJAX request URL, it should always be `'{% url "messages" %}'`. The quirk of always
 *   requiring the function caller to pass the same URL argument comes from the fact that JavaScript UI cannot use
 *   Django APIs such as `{% url %}` template tag in this case.
 * @returns {Promise<void>} Promise resolved when HTMX AJAX request finishes.
 */
export const refreshMessages = (url) =>
  htmx.ajax('GET', url, { select: '#header_messages > *', swap: 'beforeend', target: '#header_messages' });
