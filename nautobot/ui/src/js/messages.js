import htmx from 'htmx.org';

/**
 * Refresh Django messages on the page using HTMX swap.
 * @returns {Promise<void>} Promise resolved when HTMX AJAX request finishes.
 */
export const refreshMessages = () =>
  htmx.ajax('GET', '/messages/', { select: '#header_messages > *', swap: 'beforeend', target: '#header_messages' });
