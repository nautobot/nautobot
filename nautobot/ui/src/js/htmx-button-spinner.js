// Class string for the spinner. Kept in sync with Nautobot's canonical icon markup
// (`mdi ...` + `aria-hidden`) so it can be applied by swapping an existing icon's classes.
const SPINNER_CLASS = 'mdi spinner-border spinner-border-sm';

// State-tracking attributes. Read/written with plain get/set/removeAttribute rather than
// `dataset` so the names below appear verbatim everywhere they are used.
const ACTIVE_ATTR = 'data-nb-spinner-active';
const ICON_CLASS_ATTR = 'data-nb-spinner-icon-class';
const INJECTED_SPINNER_ATTR = 'data-nb-injected-spinner';

/**
 * Show a loading spinner on a `.btn` element while it issues an HTMX request.
 *
 * HTMX requests are XHR-based and never trigger the browser's native loading indicator, so a click on an HTMX button
 * gives no feedback that the request is in flight. This adds that feedback globally: whenever an element that is itself
 * the HTMX requester (`event.detail.elt`) carries the `.btn` class, a Bootstrap spinner is shown for the duration of
 * the request and removed when it completes (success or failure).
 *
 * If the button has a leading MDI icon, the icon's classes are temporarily swapped for the spinner; otherwise a spinner
 * is prepended before the label. The original state is tracked via `data-nb-*` attributes so it can be restored.
 *
 * Only elements that are themselves the requester and are `.btn` are affected -- paginator links, tree carets, the
 * sidenav favorites toggle (none are `.btn`) and non-HTMX buttons are left untouched. Submit buttons inside HTMX forms
 * are not covered, because the request fires on the `<form>`, not the button.
 * @returns {void} Do not return any value, attach event listeners.
 */
export const initializeHtmxButtonSpinner = () => {
  const onBeforeRequest = (event) => {
    const button = event.detail?.elt;
    if (!(button instanceof HTMLElement) || !button.classList.contains('btn')) {
      return;
    }
    if (button.hasAttribute(ACTIVE_ATTR)) {
      return; // A spinner is already showing for an in-flight request on this button.
    }

    const icon = button.querySelector('.mdi');
    if (icon) {
      // Temporarily replace the existing icon by swapping its classes; restored on completion.
      button.setAttribute(ICON_CLASS_ATTR, icon.className);
      icon.className = SPINNER_CLASS;
      button.setAttribute(ACTIVE_ATTR, 'icon');
    } else {
      // No icon: prepend a spinner before the label, with `me-4` providing the gap.
      const spinner = document.createElement('span');
      spinner.className = `${SPINNER_CLASS} me-4`;
      spinner.setAttribute('aria-hidden', 'true');
      spinner.setAttribute(INJECTED_SPINNER_ATTR, 'true');
      button.insertBefore(spinner, button.firstChild);
      button.setAttribute(ACTIVE_ATTR, 'injected');
    }
  };

  const onAfterRequest = (event) => {
    const button = event.detail?.elt;
    if (!(button instanceof HTMLElement) || !button.classList.contains('btn')) {
      return;
    }
    const mode = button.getAttribute(ACTIVE_ATTR);
    if (!mode) {
      return;
    }

    if (mode === 'icon') {
      const icon = button.querySelector('.mdi');
      if (icon) {
        icon.className = button.getAttribute(ICON_CLASS_ATTR);
      }
      button.removeAttribute(ICON_CLASS_ATTR);
    } else {
      button.querySelector(`[${INJECTED_SPINNER_ATTR}]`)?.remove();
    }

    button.removeAttribute(ACTIVE_ATTR);
  };

  // Body-level delegation catches every HTMX request; matches the pattern in `modal.js`.
  document.body.addEventListener('htmx:beforeRequest', onBeforeRequest);
  document.body.addEventListener('htmx:afterRequest', onAfterRequest);
};
